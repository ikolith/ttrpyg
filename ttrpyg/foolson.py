import json
import warnings

"""
This version of foolson is experimental, and creates as yet no standard.
This file is completely in the public domain.
Foolson is a serialization format like json (https://www.json.org) except:
1. Indentation instead of curly braces. For simplicity, indentation is comprised of "indentons", which each are 2 single-space characters (ASCII 0x20, U+0020), like so:  . An "indentation" at the beginning of a line is made up of one or more indentons. The key concept of indentation is that one greater level of indentation indicates the interior of a json object. Note that this means the KEYS are the thing we're primarily concerned with getting indented; indenting the values is just a side-effect (this is different from some other formats). Note that this means that to have a file of key-value pairs, the entire file must be indented by one.
2. Commas are no longer used to separate values. Instead, a single space or an indentation-respecting linebreak is thus used.
3. The keys of an object are unquoted, but cannot contain a colon. Other strings, such as object values, do have to be quoted, but are allowed to contain the low-valued block of control characters forbidden in JSON.
4. All foolson files begin with the "magic number" foolson followed by a newline (a "newline" is the line feed character U+000A) (the "magic number" foolson2, etc, as well as anything else after the foolson but before the newline, is reserved for future versions of foolson. The 1 has been omitted from the magic number of foolson version 1 because we hope it will not need additional versions.) This sequence is validated and stripped from the greater text sequence before further interpretation of the foolson file; it does not affect the values within. (If the magic number is missing, conforming foolson processors and interpreters, etc, should report error and refuse to process.)
5. All foolson files end with the "rebmun cigam" nosloof preceded by a newline (a "newline" is the line feed character U+000A) (unlike in the magic number, the rebmun cigam does not change based on version of foolson), and optionally followed by a newline as well. This sequence is validated and stripped from the greater text sequence before further interpretation of the foolson file; it does not affect the values within. (If the rebmun cigam is missing, conforming foolson processors and interpreters, etc, should report error and refuse to process.) "nosloof" is pronounced /nɔs.lʉwf/ TODO: /nɑs.lʉwf/?
6. The file extension of foolson is 🤡 (U+1F921: CLOWN FACE). While I don't imagine any program will enforce this strictly (that isn't how file extensions usually work), if you don't have the technical ability to make 🤡 the extension of a file, you probably don't have the technical ability to use the awesome power of foolson. The unregistered MIME type for foolson is "text/🤡"
7. For some reason, the ECMA-404 standard, "The JSON Data Interchange Syntax", *2nd Edition / December 2017* (and no other document, I might add) claimed JSON is "Pronounced /ˈdʒeɪ·sən/, as in “Jason and The Argonauts”." (footnote * on page iii). This is nonsense. JSON is pronounced /d͡ʒej.sɔn/. The important part is that the last vowel is not a schwa, it's a real vowel that makes a syllable that rhymes with "on" (this vowel may vary for you based on the cot-caught merger). Yes, this does mean the foolson standard has a portion in it dedidated to standardizing the pronunication of JSON. Anyhow, foolson is pronounced /fʉwl.sɔn/. Some speakers might pronounce it /fuːl.sɔn/ the immportant part is the the first syllable is just the word "fool" and the second syllable rhymes with "on".
8. Not many people realize this explicitly, but implicitly in the JSON standards is the implication that each json file/record/text may only contain one value (although this value may be a compound (like array or object) that contains many other values, itself). This is also true in foolson. Just letting you know.
9. The general idea of foolson is to be as strict in parsing as possible. (How strict? TBD.) Also, the other general idea is to be very easy to parse and then piggyback off the large number of json implementations available.
"""
indenton = "  "
foolson_magic_number = "foolson\n"
foolson_rebmun_cigam = "\nnosloof"

# TODO: this is bad, "string typing". We should have a foolson and json type that subtype of str (unless this is not pythonic). I could look into this, but I choose not to at the moment.
def foolson_to_json(
    foolson: str,
) -> str:  # TODO: consider using the "json_from_foolson" convention instead of the "foolson_to_json" convention.
    # Validate magic number:
    if foolson.startswith(foolson_magic_number):
        foolson = foolson.removeprefix(foolson_magic_number)
    else:
        raise SyntaxError(
            "The foolson data does not begin with the foolson magic number, 'foolson\n'."
        )

    # Validate rebmun cigam:
    if foolson.endswith(foolson_rebmun_cigam):
        foolson = foolson.removesuffix(foolson_rebmun_cigam)
    elif foolson.endswith(foolson_rebmun_cigam + "\n"):
        foolson = foolson.removesuffix(foolson_rebmun_cigam + "\n")
    else:
        raise SyntaxError(
            "The foolson data does not end with the foolson rebmun cigam '\nnosloof'."
        )

    json_buffer = ""
    linecount = 0
    prev_indenton_level = 0
    for (
        line
    ) in (
        foolson.splitlines()
    ):  # going line-by-line might be dumb, or might necessitate we repair the lines later, but whatever.
        linecount += 1
        stripped_line = line.lstrip(" ")
        prefix_len = len(line) - len(stripped_line)

        # extra, perhaps misguided, whitespace enforcement
        if prefix_len % len(indenton) != 0:
            raise IndentationError(
                "Indentation is not uniformly composed of whole indentons; perhaps you only typed half an indenton? An indenton, which makes a level of indentation, is two spaces. Problem is on line %d."
                % linecount
            )
        if line.lstrip() != stripped_line:
            raise IndentationError(
                "You seem to have tried to include some non-space whitespace character in the indentation. This is illegal in the foolson spec (forthcoming). Problem is on line %d."
                % linecount
            )

        # OK, let's actually do the transformation.
        indenton_count = prefix_len // len(indenton)
        if indenton_count > prev_indenton_level:
            if indenton_count == prev_indenton_level + 1:
                json_buffer += "{\n"
            else:
                raise IndentationError(
                    "You seem to have tried to indent more than one level at once, as the indenton level has gone from %d to %d. Problem is on line %d."
                    % (prev_indenton_level, indenton_count, linecount)
                )
        elif indenton_count < prev_indenton_level:
            json_buffer += "}" * (
                prev_indenton_level - indenton_count
            )  # It's perfectly fine to close multiple levels at once.
        # we always add the line of json...
        json_buffer += line
        prev_indenton_level = indenton_count
    json_buffer += (
        "}" * prev_indenton_level
    )  # as we are now done with the string, we may close all remaining json objects
    return json_buffer


def json_to_foolson(json: str) -> str:
    raise NotImplementedError(
        "Literally no one has ever needed json→foolson capability up to this point, so it has not been implemented. Please file a bug report if you need this."
    )


def values_to_foolson(obj) -> str:
    raise NotImplementedError(
        "Literally no one has ever needed value→foolson capability up to this point, so it has not been implemented. Please file a bug report if you need this."
    )


def foolson_to_values(foolson: str):
    return json.loads(foolson_to_json(foolson))


def test():
    print(foolson_to_json('foolson\n  "blah":\n    "blah": "blah"\nnosloof'))
    print(foolson_to_values('foolson\n{"blah":\n  "blah": "blah"}\nnosloof'))
    # Example from https://docs.python.org/3/library/json.html
    print(
        json.loads("""["foo", {"bar":["baz", null, 1.0, 2]}]""")
        == foolson_to_values(  # print(
            """foolson\n["foo",\n  "bar":  ["baz", null, 1.0, 2]\n]\nnosloof"""
        )
        # )
    )
    print(
        # Example from https://json.org/example.html
        json.loads(
            """
{
    "glossary": {
        "title": "example glossary",
        "GlossDiv": {
            "title": "S",
            "GlossList": {
                "GlossEntry": {
                    "ID": "SGML",
                    "SortAs": "SGML",
                    "GlossTerm": "Standard Generalized Markup Language",
                    "Acronym": "SGML",
                    "Abbrev": "ISO 8879:1986",
                    "GlossDef": {
                        "para": "A meta-markup language, used to create markup languages such as DocBook.",
                        "GlossSeeAlso": ["GML", "XML"]
                    },
                    "GlossSee": "markup"
                }
            }
        }
    }
}
"""
        )
        == foolson_to_values(
            """foolson
  "glossary": 
    "title": "example glossary",
    "GlossDiv": 
      "title": "S",
      "GlossList": 
        "GlossEntry": 
          "ID": "SGML",
          "SortAs": "SGML",
          "GlossTerm": "Standard Generalized Markup Language",
          "Acronym": "SGML",
          "Abbrev": "ISO 8879:1986",
          "GlossDef": 
            "para": "A meta-markup language, used to create markup languages such as DocBook.",
            "GlossSeeAlso": ["GML", "XML"]
          ,
          "GlossSee": "markup"
nosloof"""
        )
    )


test()
