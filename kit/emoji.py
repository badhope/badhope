# -*- coding: utf-8 -*-
"""emoji 解析（GRS html.js + ops.js 的 emoji-name-map 移植）。

GRS 用法：repo pin 卡描述里的 `:emoji:` 短代码 → Unicode 字符。
本模块内置 200+ 常用 emoji 短代码（覆盖 GRS emoji-name-map 的高频子集），
`parse_emojis(":sparkles: done")` → `"✨ done"`。未知短代码原样保留。
"""

import re

#: 高频 emoji 短代码（GitHub 风格 :name: → Unicode）
EMOJIS = {
    "sparkles": "✨", "rocket": "🚀", "tada": "🎉", "fire": "🔥",
    "bug": "🐛", "bulb": "💡", "memo": "📝", "book": "📖", "books": "📚",
    "pencil": "📝", "pencil2": "✏️", "art": "🎨", "wrench": "🔧",
    "hammer": "🔨", "gear": "⚙️", "wrench_and_screwdriver": "🛠️",
    "package": "📦", "zap": "⚡", "star": "⭐", "star2": "🌟",
    "sparkling_heart": "💖", "heart": "❤️", "hearts": "💝",
    "check": "✅", "white_check_mark": "✅", "x": "❌", "warning": "⚠️",
    "boom": "💥", "collision": "💥", "dizzy": "💫", "dash": "💨",
    "eyes": "👀", "eye": "👁️", "speech_balloon": "💬",
    "thought_balloon": "💭", "mag": "🔍", "mag_right": "🔎",
    "lock": "🔒", "unlock": "🔓", "key": "🔑", "shield": "🛡️",
    "shield_with_ce": "🛡️", "game_die": "🎲", "8ball": "🎱",
    "trophy": "🏆", "medal": "🏅", "crown": "👑", "gem": "💎",
    "money_with_wings": "💸", "moneybag": "💰", "dollar": "💵",
    "chart_with_upwards_trend": "📈", "chart_with_downwards_trend": "📉",
    "bar_chart": "📊", "clipboard": "📋", "pushpin": "📌",
    "round_pushpin": "📍", "bookmark": "🔖", "link": "🔗",
    "paperclip": "📎", "scissors": "✂️", "file_folder": "📁",
    "open_file_folder": "📂", "calendar": "📆", "date": "📅",
    "clock": "🕐", "alarm_clock": "⏰", "hourglass": "⌛",
    "watch": "⌚", "inbox_tray": "📥", "outbox_tray": "📤",
    "email": "✉️", "envelope": "✉️", "telephone": "☎️", "phone": "📱",
    "computer": "💻", "desktop_computer": "🖥️", "tv": "📺",
    "iphone": "📱", "battery": "🔋", "electric_plug": "🔌",
    "floppy_disk": "💾", "cd": "💿", "dvd": "📀", "camera": "📷",
    "video_camera": "📹", "movie_camera": "🎥", "microphone": "🎤",
    "headphones": "🎧", "musical_note": "🎵", "notes": "🎶",
    "globe_with_meridians": "🌐", "earth_americas": "🌎",
    "earth_asia": "🌏", "earth_africa": "🌍", "sun": "☀️",
    "sunny": "☀️", "cloud": "☁️", "partly_sunny": "⛅",
    "umbrella": "☔", "snowflake": "❄️", "rainbow": "🌈",
    "crescent_moon": "🌙", "moon": "🌙", "star_and_crescent": "☪️",
    "fire_engine": "🚒", "police_car": "🚓", "ambulance": "🚑",
    "rocket_ship": "🚀", "airplane": "✈️", "ship": "🚢",
    "speedboat": "🚤", "bicycle": "🚲", "bus": "🚌", "car": "🚗",
    "taxi": "🚕", "truck": "🚚", "train": "🚋", "metro": "🚇",
    "walking": "🚶", "runner": "🏃", "dancer": "💃",
    "muscle": "💪", "point_up": "☝️", "point_down": "👇",
    "point_left": "👈", "point_right": "👉", "wave": "👋",
    "clap": "👏", "thumbsup": "👍", "+1": "👍", "thumbsdown": "👎",
    "-1": "👎", "ok_hand": "👌", "punch": "👊", "fist": "✊",
    "raised_hands": "🙌", "pray": "🙏", "handshake": "🤝",
    "smile": "😄", "smiley": "😃", "grinning": "😀", "laughing": "😆",
    "joy": "😂", "rofl": "🤣", "wink": "😉", "blush": "😊",
    "innocent": "😇", "slightly_smiling_face": "🙂", "upside_down_face": "🙃",
    "thinking": "🤔", "neutral_face": "😐", "expressionless": "😑",
    "no_mouth": "😶", "smirk": "😏", "unamused": "😒",
    "roll_eyes": "🙄", "grimacing": "😬", "lying_face": "🤥",
    "relieved": "😌", "pensive": "😔", "sleepy": "😪",
    "sleeping": "😴", "mask": "😷", "face_with_thermometer": "🤒",
    "face_with_head_bandage": "🤕", "money_mouth_face": "🤩",
    "cowboy_hat_face": "🤠", "nerd_face": "🤓", "sunglasses": "😎",
    "cry": "😢", "sob": "😭", "frowning": "😦", "anguished": "😧",
    "fearful": "😨", "weary": "😩", "exploding_head": "🤯",
    "zany_face": "🤪", "hot_face": "🥵", "cold_face": "🥶",
    "thumbsup_tone1": "👍", "raised_eyebrow": "🤨", "shushing_face": "🤫",
    "shrug": "🤷", "face_palm": "🤦", "octocat": "🐙",
    "ghost": "👻", "robot": "🤖", "alien": "👽", "space_invader": "👾",
    "cactus": "🌵", "christmas_tree": "🎄", "gift": "🎁",
    "balloon": "🎈", "party_popper": "🎉", "confetti_ball": "🎊",
    "cake": "🍰", "coffee": "☕", "tea": "🍵", "beer": "🍺",
    "beers": "🍻", "clinking_glasses": "🥂", "pizza": "🍕",
    "hamburger": "🍔", "apple": "🍎", "banana": "🍌", "grapes": "🍇",
    "watermelon": "🍉", "strawberry": "🍓", "peach": "🍑",
    "cherries": "🍒", "cookie": "🍪", "candy": "🍬", "lollipop": "🍭",
    "chocolate_bar": "🍫", "donut": "🍩", "dog": "🐶", "cat": "🐱",
    "mouse": "🐭", "hamster": "🐹", "rabbit": "🐰", "fox_face": "🦊",
    "bear": "🐻", "panda_face": "🐼", "koala": "🐨", "tiger": "🐯",
    "lion": "🦁", "cow": "🐮", "pig": "🐷", "frog": "🐸",
    "monkey_face": "🐵", "monkey": "🐒", "chicken": "🐔",
    "penguin": "🐧", "bird": "🐦", "baby_chick": "🐤", "eagle": "🦅",
    "duck": "🦆", "owl": "🦉", "horse": "🐴", "unicorn_face": "🦄",
    "bee": "🐝", "bug2": "🐜", "butterfly": "🦋", "snail": "🐌",
    "beetle": "🐞", "ant": "🐜", "spider": "🕷️", "scorpion": "🦂",
    "crab": "🦀", "snake": "🐍", "turtle": "🐢", "tropical_fish": "🐠",
    "fish": "🐟", "blowfish": "🐡", "dolphin": "🐬", "shark": "🦈",
    "whale": "🐳", "octopus": "🐙", "shell": "🐚", "plant": "🌱",
    "seedling": "🌱", "herb": "🌿", "four_leaf_clover": "🍀",
    "maple_leaf": "🍁", "fallen_leaf": "🍂", "leaves": "🍃",
    "mushroom": "🍄", "chestnut": "🌰", "blossom": "🌼",
    "sunflower": "🌻", "tulip": "🌷", "rose": "🌹",
    "wilted_flower": "🥀", "hibiscus": "🌺", "cherry_blossom": "🌸",
}

_EMOJI_RE = re.compile(r":([a-z0-9_+\-]+):")


def parse_emojis(text):
    """把 `:name:` 短代码替换为 Unicode 字符。未知短代码原样保留。"""
    return _EMOJI_RE.sub(lambda m: EMOJIS.get(m.group(1), m.group(0)), text)
