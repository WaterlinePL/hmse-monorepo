import random


def generate_random_html_color_solid() -> str:
    return f"rgba({__rand_channel_val()}, {__rand_channel_val()}, {__rand_channel_val()}, 1.0)"


def generate_random_html_color_transparent() -> str:
    return f"rgba({__rand_channel_val()}, {__rand_channel_val()}, {__rand_channel_val()}, 0.5)"

def __rand_channel_val():
    return random.randint(0, 255)
