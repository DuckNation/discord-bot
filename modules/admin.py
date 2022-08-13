import heapq
import io
import os
import re
import zlib
from difflib import SequenceMatcher

import discord
import pytz
from discord.ext import commands


def ratio(a, b):
    m = SequenceMatcher(None, a, b)
    return int(round(100 * m.ratio()))


def quick_ratio(a, b):
    m = SequenceMatcher(None, a, b)
    return int(round(100 * m.quick_ratio()))


def partial_ratio(a, b):
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    m = SequenceMatcher(None, short, long)

    blocks = m.get_matching_blocks()

    scores = []
    for i, j, n in blocks:
        start = max(j - i, 0)
        end = start + len(short)
        o = SequenceMatcher(None, short, long[start:end])
        r = o.ratio()

        if 100 * r > 99:
            return 100
        scores.append(r)

    return int(round(100 * max(scores)))


_word_regex = re.compile(r"\W", re.IGNORECASE)


def _sort_tokens(a):
    a = _word_regex.sub(" ", a).lower().strip()
    return " ".join(sorted(a.split()))


def token_sort_ratio(a, b):
    a = _sort_tokens(a)
    b = _sort_tokens(b)
    return ratio(a, b)


def quick_token_sort_ratio(a, b):
    a = _sort_tokens(a)
    b = _sort_tokens(b)
    return quick_ratio(a, b)


def partial_token_sort_ratio(a, b):
    a = _sort_tokens(a)
    b = _sort_tokens(b)
    return partial_ratio(a, b)


def _extraction_generator(query, choices, scorer=quick_ratio, score_cutoff=0):
    try:
        for key, value in choices.items():
            score = scorer(query, key)
            if score >= score_cutoff:
                yield key, score, value
    except AttributeError:
        for choice in choices:
            score = scorer(query, choice)
            if score >= score_cutoff:
                yield choice, score


def extract(query, choices, *, scorer=quick_ratio, score_cutoff=0, limit=10):
    it = _extraction_generator(query, choices, scorer, score_cutoff)

    def key(t):
        return t[1]

    if limit is not None:
        return heapq.nlargest(limit, it, key=key)
    return sorted(it, key=key, reverse=True)


def extract_one(query, choices, *, scorer=quick_ratio, score_cutoff=0):
    it = _extraction_generator(query, choices, scorer, score_cutoff)

    def key(t):
        return t[1]

    try:
        return max(it, key=key)
    except Exception:
        # iterator could return nothing
        return None


def extract_or_exact(query, choices, *, limit=None, scorer=quick_ratio, score_cutoff=0):
    matches = extract(
        query,
        choices,
        scorer=scorer,
        score_cutoff=score_cutoff,
        limit=limit,
    )
    if len(matches) == 0:
        return []

    if len(matches) == 1:
        return matches

    top = matches[0][1]
    second = matches[1][1]

    # check if the top one is exact or more than 30% more correct
    # than the top
    if top == 100 or top > (second + 30):
        return [matches[0]]

    return matches


def extract_matches(query, choices, *, scorer=quick_ratio, score_cutoff=0):
    matches = extract(
        query,
        choices,
        scorer=scorer,
        score_cutoff=score_cutoff,
        limit=None,
    )
    if len(matches) == 0:
        return []

    top_score = matches[0][1]
    to_return = []
    index = 0
    while True:
        try:
            match = matches[index]
        except IndexError:
            break
        else:
            index += 1

        if match[1] != top_score:
            break

        to_return.append(match)
    return to_return


def finder(text, collection, *, key=None, lazy=True):
    suggestions = []
    text = str(text)
    pat = ".*?".join(map(re.escape, text))
    regex = re.compile(pat, flags=re.IGNORECASE)
    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)
        if r:
            suggestions.append((len(r.group()), r.start(), item))

    def sort_key(tup):
        if key:
            return tup[0], tup[1], key(tup[2])
        return tup

    if lazy:
        return (z for _, _, z in sorted(suggestions, key=sort_key))
    else:
        return [z for _, _, z in sorted(suggestions, key=sort_key)]


def find(text, collection, *, key=None):
    try:
        return finder(text, collection, key=key, lazy=False)[0]
    except IndexError:
        return None


def get_size(_bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if _bytes < factor:
            return f"{_bytes:.2f}{unit}{suffix}"
        _bytes /= factor


class SphinxObjectFileReader:
    # Inspired by Sphinx'hiss InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode("utf-8")

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b""
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b"\n")
            while pos != -1:
                yield buf[:pos].decode("utf-8")
                buf = buf[pos + 1 :]
                pos = buf.find(b"\n")


timezone = pytz.timezone("America/Chicago")


class Admin(commands.Cog):
    def __init__(self, bot):
        self.default = None
        self.author = None
        self.bot: commands.Bot = bot

    async def cog_check(self, ctx):
        return ctx.author.id in self.bot.owner_ids

    def parse_object_inv(self, stream, url):
        result = {}

        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]

        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:
                continue

            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            if projname == "discord.py":
                key = key.replace("discord.ext.commands.", "").replace("discord.", "")

            result[f"{prefix}{key}"] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            sub = cache[key] = {}
            async with self.bot.session.get(page + "/objects.inv") as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        "Cannot build rtfm lookup table, try again later."
                    )

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx, key, obj):
        page_types = {
            "latest": "https://discordpy.readthedocs.io/en/latest",
            "latest-jp": "https://discordpy.readthedocs.io/ja/latest",
            "python": "https://docs.python.org/3",
            "python-jp": "https://docs.python.org/ja/3",
            "master": "https://discordpy.readthedocs.io/en/master",
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not hasattr(self, "_rtfm_cache"):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", obj)

        if key.startswith("latest"):
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == "_":
                    continue
                if q == name:
                    obj = f"abc.Messageable.{name}"
                    break

        cache = list(self._rtfm_cache[key].items())

        matches = finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        e = discord.Embed(colour=0xFF00FF)
        if len(matches) == 0:
            return await ctx.send("Could not find anything. Sorry.")

        e.description = "\n".join(f"[`{key}`]({url})" for key, url in matches)
        await ctx.reply(embed=e)

    def transform_rtfm_language_key(self, ctx, prefix):
        if ctx.guild is not None:
            if ctx.channel.category_id == 490287576670928914:
                return prefix + "-jp"
            elif ctx.guild.id in (463986890190749698, 494911447420108820):
                return prefix + "-jp"
        return prefix

    @commands.command()
    @commands.is_owner()
    async def reload_commands(self, ctx: commands.Context, all=False):
        await ctx.send("Syncing command tree.")
        if all:
            await self.bot.tree.sync()
            await ctx.send("Synced global commands!")
        else:
            await self.bot.tree.sync(guild=discord.Object(id=790774812690743306))
            await ctx.send("Synced guild commands!")

    @commands.group(aliases=["rtfd"], invoke_without_command=True, hidden=True)
    async def rtfm(self, ctx, *, obj: str = None):
        key = self.transform_rtfm_language_key(ctx, "master")
        await self.do_rtfm(ctx, key, obj)

    @rtfm.command(name="python", aliases=["py"], hidden=True)
    @commands.is_owner()
    async def rtfm_python(self, ctx, *, obj: str = None):
        key = self.transform_rtfm_language_key(ctx, "python")
        await self.do_rtfm(ctx, key, obj)

    @rtfm.command(name="master", aliases=["joshy"], hidden=True)
    @commands.is_owner()
    async def rtfm_master(self, ctx, *, obj: str = None):
        key = self.transform_rtfm_language_key(ctx, "master")
        await self.do_rtfm(ctx, key, obj)


async def setup(bot):
    await bot.add_cog(Admin(bot))
