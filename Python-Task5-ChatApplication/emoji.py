"""Display-only emoji shortcode replacements for the chat client."""

EMOJI_SHORTCODES = {
    ":smile:": "😄", ":grin:": "😁", ":joy:": "😂", ":rofl:": "🤣",
    ":love:": "❤️", ":heart:": "❤️", ":fire:": "🔥", ":thumbsup:": "👍",
    ":thumbsdown:": "👎", ":clap:": "👏", ":ok_hand:": "👌", ":wave:": "👋",
    ":pray:": "🙏", ":cry:": "😢", ":sob:": "😭", ":angry:": "😠",
    ":thinking:": "🤔", ":eyes:": "👀", ":star:": "⭐", ":sparkles:": "✨",
    ":rocket:": "🚀", ":tada:": "🎉", ":party:": "🥳", ":check:": "✅",
    ":x:": "❌", ":warning:": "⚠️", ":poop:": "💩", ":skull:": "💀",
    ":cool:": "😎", ":100:": "💯",
}


def replace_shortcodes(text: str) -> str:
    for shortcode, emoji in EMOJI_SHORTCODES.items():
        text = text.replace(shortcode, emoji)
    return text
