from telegram import BotCommand

import os

SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/SoulMeetsHQ")
UPDATE_LINK = os.getenv("UPDATE_LINK", "https://t.me/WorkGlows")
GROUP_LINK = "https://t.me/SoulMeetsHQ"
BROADCAST_DELAY = 0.03

# Commands dictionary
COMMANDS = [
    BotCommand("start", "👋 Wake me up"),
    BotCommand("buy", "🌸 Get flowers"),
    BotCommand("buyers", "💝 Flower buyers"),
    BotCommand("help", "💬 A short guide")
]

# EMOJI REACTIONS AND STICKERS
# Emoji reactions for /start command
EMOJI_REACT = [
    "🍓",  "💊",  "🦄",  "💅",  "💘",
    "💋",  "🍌",  "⚡",  "🕊️",  "❤️‍🔥",
    "🔥",  "❤️"
]

# TELETHON EFFECTS CONFIGURATION
EFFECTS = [
    "5104841245755180586",
    "5159385139981059251"
]

# Stickers for after /start command
START_STICKERS = [
    "CAACAgUAAxkBAAEPHVRomHVszeSnrB2qQBGNHy6BgyZAHwACvxkAAmpxyFT7N37qhVnGmzYE",
    "CAACAgUAAxkBAAEPHVVomHVsuGrU-zEa0X8i1jn_HW7XawAC-BkAArnxwVRFqeVbp2Mn_TYE",
    "CAACAgUAAxkBAAEPHVZomHVsuf3QWObxnD9mavVnmS4XPgACPhgAAqMryVT761H_MmILCjYE",
    "CAACAgUAAxkBAAEPHVdomHVs87jwVjxQjM7k37cUAwnJXQACwxYAAs2CyFRnx4YgWFPZkjYE",
    "CAACAgUAAxkBAAEPHVhomHVsnB4iVT8jr56ZtGPq98KQeQACfRgAAoQAAcBUyVgSjnENUUo2BA",
    "CAACAgUAAxkBAAEPHVlomHVsRWNXE2vkgSYrBU9K-JB9UwACoxcAAi4MyFS0w-gqFTBWQjYE",
    "CAACAgUAAxkBAAEPHVpomHVsfUZT06tR7jgqmHNJA-j5fAACpBgAAuhZyVSaY0y3w0zVLjYE",
    "CAACAgUAAxkBAAEPHVtomHVsqjujca8HBOPQpEvJY-I0WQACZRQAAhX0wFS2YntXBMU6ATYE",
    "CAACAgUAAxkBAAEPHVxomHVsw09_FKmfugTeaqTXrIOMNwACzhQAAlyLwFSL4-96tJu0STYE",
    "CAACAgUAAxkBAAEPHV1omHVsP9aNtLlGJyErPF8yEvuuawAC6RcAAj7DwFSKnv319y6jnTYE",
    "CAACAgUAAxkBAAEPHV5omHVsuz9c3bxncAXOQ6BDzhrTnwACKxwAAm4QwVRdrk0EgrotFjYE",
    "CAACAgUAAxkBAAEPHV9omHVs3df-rmdlDbJFu-MREg5RrwAC5RYAAsCewVSvwTepiO6BlTYE",
    "CAACAgUAAxkBAAEPHWBomHVshaztRlsJ2d3p6qV1TAolvgACChkAAjf9wFSqz_XgZVhTLTYE",
    "CAACAgUAAxkBAAEPHWFomHVsrjl_UqIUYgs8NUKycyXbuQAChRgAApa6wFQoEbjt-4UEUDYE",
    "CAACAgUAAxkBAAEPHWJomHVssUsAAU8BbI1lcPdQ2hJbbrwAAg4YAAI4lchULkVARTsFmjI2BA",
    "CAACAgUAAxkBAAEPHWNomHVs0wFx3n8i8r6TefoJzP_3XAACqRYAAvKvyFQiY8XErd3KFDYE",
    "CAACAgUAAxkBAAEPHWRomHVsXNHMWzXxpKxSrze5yM0kzAACRx4AAt7oyFS3n9YnyqQwCjYE",
    "CAACAgUAAxkBAAEPHWVomHVsQxKxih6IfqUeZ7aQaCXBvAACyBgAAkHPwVT8uW_J5GUHQTYE",
    "CAACAgUAAxkBAAEPHWZomHVsFSeBqaNqm5rWNu8LdszNcAACxhUAAuEtwVQi2t0gazmalDYE",
    "CAACAgUAAxkBAAEPHWdomHVsFOXCOM_DZb1VuGPlXfkY2AAC4RgAAu2CwVSxJETZ5OhUGTYE",
    "CAACAgUAAxkBAAEPHWhomHVsovXP8XqbvEjEB508DTW6VQAC2BcAAoJLwFRRhczsSdgAASg2BA",
    "CAACAgUAAxkBAAEPHWlomHVsNkxBtCovGit7bjWNEV5kTwACFhYAArQ9wFRAwzg1qA0TrTYE",
    "CAACAgUAAxkBAAEPHWpomHVs8vADDgs56H30a5uM2uNvhQACtxcAAj_QQVSXTCvC5zEIPjYE",
    "CAACAgUAAxkBAAEPHWtomHVsS466sNdxHk4lGsza3S_3yQAC9B0AAnZtQFQJYcwEnXCS6DYE",
    "CAACAgUAAxkBAAEPJzFonedaEsY_x_cVxB5i5WHRmYDfZwACdBgAAnTX8VThqO2DUegdyjYE"
]

# Sakura stickers list
SAKURA_STICKERS = [
    "CAACAgUAAxkBAAEPHYZomHbXHoaO5ZgAAWfmDG76TNdc0SgAAlMXAALQK6hV0eIcUy6BTnw2BA",
    "CAACAgUAAxkBAAEPHYdomHbXn4W5q5NZwaBXrIyH1vIQLAACthQAAvfkqVXP72iQq0BNejYE",
    "CAACAgUAAxkBAAEPHYhomHbX0HF-54Br14uoez3P0CnN1QACVhQAAiwMqFUXDEHvVKsJLTYE",
    "CAACAgUAAxkBAAEPHYlomHbXp0TzjPbKW-6vD4UZIMf1LgACmRsAAmwjsFWFJ6owU1WfgTYE",
    "CAACAgUAAxkBAAEPHYpomHbXPrYvs4bqejy5OUzzDS0oFwACVigAAr4JsVWLUPaAp8o1mDYE",
    "CAACAgUAAxkBAAEPHYtomHbXBs9aqV9_RA1ChGdZuof4zQACLxYAAsdcqVWCxB2Z-fbRGDYE",
    "CAACAgUAAxkBAAEPHYxomHbXCrWKildzkNTAchdFzbrMBQAC0xkAAupDqVUMuhU5w3qV5TYE",
    "CAACAgUAAxkBAAEPHY1omHbXE6Rdmv2m6chyBV_HH9u8XwACAhkAAjKHqVWAkaO_ky9lTzYE",
    "CAACAgUAAxkBAAEPHY5omHbXujQsxWB6OsTuyCTtOk2nlAACKxYAAhspsFV1qXoueKQAAUM2BA",
    "CAACAgUAAxkBAAEPHY9omHbX7S-80hbGGWRuLVj_wtKqygACXxkAAj60sVXgsb-vzSnt_TYE",
    "CAACAgUAAxkBAAEPHZBomHbXUxsXqH2zbJFK1GOiZzDcCwACuRUAAo2isVWykxNLWnwcYTYE",
    "CAACAgUAAxkBAAEPHZFemHbXjRN4Qa9WUbcWlRECLPp6NAACRx4AAp2SqFXcarUkpU5jzjYE",
    "CAACAgUAAxkBAAEPHZJomHbXX_4GTnA25ivpOWqe1UC66QACaBQAAu0uqFXKL-cNi_ZBJDYE",
    "CAACAgUAAxkBAAEPHZNomHbXWqwAAeuc7FCe0yCUd3DVx5YAAq8YAALcXbBVTI07io7mR2Q2BA",
    "CAACAgUAAxkBAAEPHZRomHbXxi3SDeeUOnqON0D3czFrEAACCxcAAidVsFWEt7xrqmGJxjYE",
    "CAACAgUAAxkBAAEPHZVomHbXjFFKT2Ks98KxKiTEab_NDAACEBkAAg7VqFV6tAlBFHKdPDYE",
    "CAACAgUAAxkBAAEPHZZomHbXtQ5QRjobH7M6Ys-5XO-IQQACrhQAArcDsVV3-V8JhPN1qDYE",
    "CAACAgUAAxkBAAEPHZdomHbXDL-13xEyhcVV2bAIRun90AACIBoAAquXsVX6KNOab-JSkzYE",
    "CAACAgUAAxkBAAEPHZhomHbX3mK-IPSpEpnrTVqc36bR6AACHxUAArG-qFU5OStAsdYoJTYE",
    "CAACAgUAAxkBAAEPHZlomHbXdqlqWs00NKAOToK90LgPpgACsRUAAiqIsVULIgcY4EYPbzYE",
    "CAACAgUAAxkBAAEPHZpomHbXPh9D5VSlhmSX2HEIClk92AACPxcAArtosFXxg3weTZPx5TYE",
    "CAACAgUAAxkBAAEPHZtomHbXpeFGlpeqcKIrzEsxC7PCkAACdxQAAhX8qVW1te9rkWttOzYE",
    "CAACAgUAAxkBAAEPHZxomHbXSi44c4Umy_H5JxN7BY8-8QACtRcAAtggqVVx1D8N-Hwp8TYE",
    "CAACAgUAAxkBAAEPHZ1omHbXIuMqO0K098jc3On6mCgQYAAC5hoAAnAbcFe9bbelWKStUTYE",
    "CAACAgUAAxkBAAEPHZ5omHbXVHEhhoXyZlaTtXG5YNhUwwACQhUAAqGYqFXmCuT6Lrdn-jYE",
    "CAACAgUAAxkBAAEPHZ9omHbXuHwrW1hOKXwYn9euLXxufQACHxgAAvpMqVWpxtBkEZPfPjYE",
    "CAACAgUAAxkBAAEPHaBomHbXge6qzFuLoA_ahtyIe9ptVgAC6x4AAiU7sVUROxvmQwqc0zYE",
    "CAACAgUAAxkBAAEPHaFomHbXG7wOX3wP-PNMH5uBmZqZvwACnhMAAilDsVUIsplzTkTefTYE",
    "CAACAgUAAxkBAAEPHaJomHbX3Q6jptPInCK75s45AAHneSsAArsUAAJp9qhV4C7LO05mEJM2BA",
    "CAACAgUAAxkBAAEPHaNomHbX3Q6jptPInCK75s45AAHneSsAArsUAAJp9qhV4C7LO05mEJM2BA",
    "CAACAgUAAxkBAAEPHaRomHbXia_R6dE0FmqOKe-b3CcLkgACKBkAAjb_4FVt48Cz-d5N1jYE",
    "CAACAgUAAxkBAAEPC_xoizPIGzAQCLzAjUzmRbgMYxeKbQACmRcAAnUn-VUG3_UOew4L4jYE",
    "CAACAgUAAxkBAAEPHaZomHbXCr_dCMvWOkTWL43UFUlWngACRhcAApNn8FZtvNjsiOa9nDYE",
    "CAACAgUAAxkBAAEPHadomHbXozU4tnToM5GOyR0SoYwGfQACRhYAAozAYVfKp8CwOkHT_jYE",
    "CAACAgUAAxkBAAEPHahomHbX77Pd3U0UOXwHu2GlDtisjQACVxcAAoppcVfvp-s9H4KEAzYE",
    "CAACAgUAAxkBAAEPHalomHbXG2fob7X9N-ozzyO1bDKRewACtBcAAsQ1cFcYpoovBrL4VDYE",
    "CAACAgUAAxkBAAEPHapomHbX04Yr2aCsKvkKaS8CuliIhgACrRMAAoRscFc4LHU4Cx_vCjYE",
    "CAACAgUAAxkBAAEPHatomHbXukYsQKH0Bs9SPoSmX_RhHgAC_xcAAjJPcFfbZKwhO2drjTYE",
    "CAACAgUAAxkBAAEPHaxomHbXSnidTo6q58ZX6L1_cVB3tQAClRYAAgFGaVeg-WgjAriwmzYE",
    "CAACAgUAAxkBAAEPHa1omHbXIuMqO0K098jc3On6mCgQYAAC5hoAAnAbcFe9bbelWKStUTYE",
    "CAACAgUAAxkBAAEPHa5omHbXoQe84QFvlQQlhNyKOzKUywAC9hcAArKQeVdTfgpzto8-mzYE",
    "CAACAgUAAxkBAAEPHa9omHbXPIpqHjgVWzVgmDohWt1WPAACpRUAArd2eVfJQarwwTKHazYE",
    "CAACAgUAAxkBAAEPHbBomHbXP5djg5YjJcKzaOnx_H6r_gACchUAAmVTgVe4fFRoDNGbQjYE",
    "CAACAgUAAxkBAAEPHbFomHbXEsoNl8q72uhyni6zRlDLiwACdRsAArzsgFcFaB5SZVJGmjYE",
    "CAACAgUAAxkBAAEPHbJomHbXGmztGeyRFxKICMyMeg5OYwACOxwAAqs6kVefWA1lG-qbKTYE",
    "CAACAgUAAxkBAAEPHbNomHbXOf8ffPWF1xOGw1ZVkKlH5QACUhkAAjyxmFcalZ9vPMc3BDYE",
    "CAACAgUAAxkBAAEPHbRomHbXhAT_ICabxC1mVdGeTvAacgACaxUAAhnVoFe3aPP_2ootQjYE",
    "CAACAgUAAxkBAAEPHbVomHbXawaj7Rzgrrj7Njd54dgbMAACqBYAAkhooVftJHkaW9J31zYE",
    "CAACAgUAAxkBAAEPHbZomHbXV3da8Rkgyp8RqexV84DPPwACBRsAAg4-oVctGwxN0lRv-zYE",
    "CAACAgUAAxkBAAEPHbdomHbX3l7Hm2et2D6hO5JFzFiKZgAC3BgAAiwJoFe65x8OnZGa6zYE",
    "CAACAgUAAxkBAAEPHbhomHbXA4jAd74Nlq9x6F5Ahi36ggACvRUAAp6vsVefp9E7-1xQ2zYE",
    "CAACAgUAAxkBAAEPHblomHbXUMwbfoo8TV7lXP1dgau8BAACdhcAAl7w0VdQSujQZJElODYE",
    "CAACAgUAAxkBAAEPHbpomHbXspHoRPrE8a36vnJw6diFjwACRhMAAg6w0FdJfQABKjxnTNI2BA",
    "CAACAgUAAxkBAAEPHbtomHbXZiF5VuJ0E5UZq9Ip16d1HAACsBcAAipSyFcdvir6IIjTkTYE",
    "CAACAgUAAxkBAAEPHbxomHbXfGsuWIZO7t1cxWaPAAGvGroAAhsWAAKxgclX3iuTe-84UQE2BA",
    "CAACAgUAAxkBAAEPHb1omHbXC0SYqQ0_7kDg5T01Hs1bfwACgBkAAmLbyFeRm-Xv7FhE9TYE",
    "CAACAgUAAxkBAAEPHb5omHbXLNKidlP7lGOLoL1EdDdMJwACQRgAAuLEyVfJI1470HOHnjYE"
]

# Sakura images for start command
SAKURA_IMAGES = [
    "https://ik.imagekit.io/asadofc/Images1.png",
    "https://ik.imagekit.io/asadofc/Images2.png",
    "https://ik.imagekit.io/asadofc/Images3.png",
    "https://ik.imagekit.io/asadofc/Images4.png",
    "https://ik.imagekit.io/asadofc/Images5.png",
    "https://ik.imagekit.io/asadofc/Images6.png",
    "https://ik.imagekit.io/asadofc/Images7.png",
    "https://ik.imagekit.io/asadofc/Images8.png",
    "https://ik.imagekit.io/asadofc/Images9.png",
    "https://ik.imagekit.io/asadofc/Images10.png",
    "https://ik.imagekit.io/asadofc/Images11.png",
    "https://ik.imagekit.io/asadofc/Images12.png",
    "https://ik.imagekit.io/asadofc/Images13.png",
    "https://ik.imagekit.io/asadofc/Images14.png",
    "https://ik.imagekit.io/asadofc/Images15.png",
    "https://ik.imagekit.io/asadofc/Images16.png",
    "https://ik.imagekit.io/asadofc/Images17.png",
    "https://ik.imagekit.io/asadofc/Images18.png",
    "https://ik.imagekit.io/asadofc/Images19.png",
    "https://ik.imagekit.io/asadofc/Images20.png",
    "https://ik.imagekit.io/asadofc/Images21.png",
    "https://ik.imagekit.io/asadofc/Images22.png",
    "https://ik.imagekit.io/asadofc/Images23.png",
    "https://ik.imagekit.io/asadofc/Images24.png",
    "https://ik.imagekit.io/asadofc/Images25.png",
    "https://ik.imagekit.io/asadofc/Images26.png",
    "https://ik.imagekit.io/asadofc/Images27.png",
    "https://ik.imagekit.io/asadofc/Images28.png",
    "https://ik.imagekit.io/asadofc/Images29.png",
    "https://ik.imagekit.io/asadofc/Images30.png",
    "https://ik.imagekit.io/asadofc/Images31.png",
    "https://ik.imagekit.io/asadofc/Images32.png",
    "https://ik.imagekit.io/asadofc/Images33.png",
    "https://ik.imagekit.io/asadofc/Images34.png",
    "https://ik.imagekit.io/asadofc/Images35.png",
    "https://ik.imagekit.io/asadofc/Images36.png",
    "https://ik.imagekit.io/asadofc/Images37.png",
    "https://ik.imagekit.io/asadofc/Images38.png",
    "https://ik.imagekit.io/asadofc/Images39.png",
    "https://ik.imagekit.io/asadofc/Images40.png"
]

# MESSAGE DICTIONARIES
# Star Payment Messages Dictionaries
INVOICE_DESCRIPTIONS = [
    "Welcome to our flowers stall! 🌸✨",
    "Take beautiful sakura flowers! 🌸💫",
    "Pick your favorite cherry blossoms! 🌸🌟",
    "Get fresh flowers from our stall! 🌸🦋"
]

THANK_YOU_MESSAGES = [
    "🌸 Thanks for taking flowers from our stall! Come back anytime! 💕",
    "✨ Thank you for visiting our flower stall! Your flowers are beautiful! 🌸",
    "🌟 Thanks for choosing our sakura stall! Enjoy your flowers! 🌸❤️",
    "🌸 Thank you for shopping at our flower stall! See you again! ✨",
    "💫 Thanks for getting flowers from us! Have a lovely day! 🌸"
]

REFUND_MESSAGES = [
    "🌸 Thanks for showing such kindness! We are returning your payment for your generosity! 💕",
    "✨ Your kindness touched our hearts! We're refunding your payment as a gesture of appreciation! 🌸",
    "🌟 Such a kind soul! We're returning your stars because your kindness means more to us! 🌸❤️",
    "🌸 Your gentle spirit deserves this refund! Thank you for being so wonderfully kind! ✨",
    "💫 We're touched by your kindness! Here's your refund as our way of saying thank you! 🌸"
]

PAYMENT_STICKERS = [
    "CAACAgUAAxkBAAEPHVRomHVszeSnrB2qQBGNHy6BgyZAHwACvxkAAmpxyFT7N37qhVnGmzYE",
    "CAACAgUAAxkBAAEPHVVomHVsuGrU-zEa0X8i1jn_HW7XawAC-BkAArnxwVRFqeVbp2Mn_TYE",
    "CAACAgUAAxkBAAEPHVZomHVsuf3QWObxnD9mavVnmS4XPgACPhgAAqMryVT761H_MmILCjYE",
    "CAACAgUAAxkBAAEPHVdomHVs87jwVjxQjM7k37cUAwnJXQACwxYAAs2CyFRnx4YgWFPZkjYE",
    "CAACAgUAAxkBAAEPHVhomHVsnB4iVT8jr56ZtGPq98KQeQACfRgAAoQAAcBUyVgSjnENUUo2BA",
    "CAACAgUAAxkBAAEPHVlomHVsRWNXE2vkgSYrBU9K-JB9UwACoxcAAi4MyFS0w-gqFTBWQjYE",
    "CAACAgUAAxkBAAEPHVpomHVsfUZT06tR7jgqmHNJA-j5fAACpBgAAuhZyVSaY0y3w0zVLjYE",
    "CAACAgUAAxkBAAEPHVtomHVsqjujca8HBOPQpEvJY-I0WQACZRQAAhX0wFS2YntXBMU6ATYE",
    "CAACAgUAAxkBAAEPHVxomHVsw09_FKmfugTeaqTXrIOMNwACzhQAAlyLwFSL4-96tJu0STYE",
    "CAACAgUAAxkBAAEPHV1omHVsP9aNtLlGJyErPF8yEvuuawAC6RcAAj7DwFSKnv319y6jnTYE",
    "CAACAgUAAxkBAAEPHV5omHVsuz9c3bxncAXOQ6BDzhrTnwACKxwAAm4QwVRdrk0EgrotFjYE",
    "CAACAgUAAxkBAAEPHV9omHVs3df-rmdlDbJFu-MREg5RrwAC5RYAAsCewVSvwTepiO6BlTYE",
    "CAACAgUAAxkBAAEPHWBomHVshaztRlsJ2d3p6qV1TAolvgACChkAAjf9wFSqz_XgZVhTLTYE",
    "CAACAgUAAxkBAAEPHWFomHVsrjl_UqIUYgs8NUKycyXbuQAChRgAApa6wFQoEbjt-4UEUDYE",
    "CAACAgUAAxkBAAEPHWJomHVssUsAAU8BbI1lcPdQ2hJbbrwAAg4YAAI4lchULkVARTsFmjI2BA",
    "CAACAgUAAxkBAAEPHWNomHVs0wFx3n8i8r6TefoJzP_3XAACqRYAAvKvyFQiY8XErd3KFDYE",
    "CAACAgUAAxkBAAEPHWRomHVsXNHMWzXxpKxSrze5yM0kzAACRx4AAt7oyFS3n9YnyqQwCjYE",
    "CAACAgUAAxkBAAEPHWVomHVsQxKxih6IfqUeZ7aQaCXBvAACyBgAAkHPwVT8uW_J5GUHQTYE",
    "CAACAgUAAxkBAAEPHWZomHVsFSeBqaNqm5rWNu8LdszNcAACxhUAAuEtwVQi2t0gazmalDYE",
    "CAACAgUAAxkBAAEPHWdomHVsFOXCOM_DZb1VuGPlXfkY2AAC4RgAAu2CwVSxJETZ5OhUGTYE",
    "CAACAgUAAxkBAAEPHWhomHVsovXP8XqbvEjEB508DTW6VQAC2BcAAoJLwFRRhczsSdgAASg2BA",
    "CAACAgUAAxkBAAEPHWlomHVsNkxBtCovGit7bjWNEV5kTwACFhYAArQ9wFRAwzg1qA0TrTYE",
    "CAACAgUAAxkBAAEPHWpomHVs8vADDgs56H30a5uM2uNvhQACtxcAAj_QQVSXTCvC5zEIPjYE",
    "CAACAgUAAxkBAAEPHWtomHVsS466sNdxHk4lGsza3S_3yQAC9B0AAnZtQFQJYcwEnXCS6DYE",
    "CAACAgUAAxkBAAEPJzFonedaEsY_x_cVxB5i5WHRmYDfZwACdBgAAnTX8VThqO2DUegdyjYE"
]

# Start Command Messages Dictionary
START_MESSAGES = {
    "initial_caption": """
<b>Hi {user_mention}, I'm Sakura!</b> 🌸
""",
    "info_caption": """
🌸 <b>Welcome {user_mention}, I'm Sakura!</b>

Join our channel for updates! Be part of our group or add me to yours. 💓

<blockquote>💞 Let's make memories together</blockquote>
""",
    "button_texts": {
        "info": "📒 Info",
        "hi": "👋 Hello",
        "updates": "🗯️️ Updates",
        "support": "💕 Support",
        "add_to_group": "🫂 Add Me To Your Group"
    },
    "callback_answers": {
        "info": "📒 Join our channel and group for more!",
        "hi": "👋 Hey there, Let's chat! What's on your mind?"
    }
}

# Help Command Messages Dictionary
HELP_MESSAGES = {
    "minimal": """
🌸 <b>Short Guide for {user_mention}</b>

✨ I'm your helpful friend
💭 You can ask me anything
🫶 Let's talk in simple Hindi

<i>Tap the button below to expand the guide</i> ⬇️
""",
    "expanded": """
🌸 <b>Short Guide for {user_mention}</b> 🌸

🗣️ Talk in Hindi, English, or Bangla
💭 Ask simple questions
🎓 Help with study, advice, or math
🎭 Send a sticker, I'll send one too
❤️ Kind, caring, and always here

<i>Let's talk! 🫶</i>
""",
    "button_texts": {
        "expand": "📖 Expand Guide",
        "minimize": "📚 Minimize Guide"
    },
    "callback_answers": {
        "expand": "📖 Guide expanded! Check all features",
        "minimize": "📚 Guide minimized for quick view"
    }
}

# Broadcast Command Messages Dictionary
BROADCAST_MESSAGES = {
    "select_target": """
📣 <b>Select Broadcast Target:</b>

👥 <b>Users:</b> {users_count} individual chats
📢 <b>Groups:</b> {groups_count} group chats

📊 <b>Total tracked:</b> {users_count} users, {groups_count} groups

After selecting, send your broadcast message (text, photo, sticker, voice, etc.):
""",
    "ready_users": """
✅ <b>Ready to broadcast to {count} users</b>

Send your message now (text, photo, sticker, voice, video, document, etc.)
It will be automatically broadcasted to all users.
""",
    "ready_groups": """
✅ <b>Ready to broadcast to {count} groups</b>

Send your message now (text, photo, sticker, voice, video, document, etc.)
It will be automatically broadcasted to all groups.
""",
    "progress": "📡 Broadcasting to {count} {target_type}...",
    "completed": """
✅ <b>Broadcast Completed!</b>

📊 Sent to: {success_count}/{total_count} {target_type}
❌ Failed: {failed_count}
""",
    "no_targets": "❌ No {target_type} found",
    "failed": "❌ Broadcast failed: {error}",
    "button_texts": {
        "users": "👥 Users ({count})",
        "groups": "📢 Groups ({count})"
    },
    "callback_answers": {
        "users": "👥 Broadcasting to users selected!",
        "groups": "📢 Broadcasting to groups selected!"
    }
}

# Fallback responses for when API is unavailable or errors occur
RESPONSES = [
    "Got a bit confused, try again 😔",
    "Something's off, I can't understand 😕",
    "I'm a little overwhelmed right now, let's talk later 🥺",
    "My brain's all scrambled, hold on 😅",
    "There's some issue with the system 🫤",
    "Network's acting up, try once more 😐",
    "I can't speak properly right now 😪",
    "Facing a technical issue 🤨",
    "I'm feeling a bit slow today 😴",
    "Looks like the server's having a bad day 😑",
    "Hang on a bit, things will get better 🙃",
    "I want to say something but can't find the words 🥺",
    "My brain just froze 🫠",
    "Might be a connection issue 😬",
    "Can't really focus at the moment 😌",
    "There's some technical glitch going on 😕",
    "Might need a quick system reboot 🫤",
    "I'm kinda in a confused state 😵",
    "The API seems moody today 😤",
    "Just a little patience, I'll be fine 💗"
]

ERROR = [
    "Sorry buddy, something went wrong 😔",
    "Oops, I think I misunderstood 🫢",
    "That was unexpected, try again 😅",
    "I'm not working properly right now 😕",
    "There's some technical problem 🤨",
    "Looks like there's a bug in the system 🫤",
    "I'm kind of frozen at the moment 😐",
    "Got an error, send the message again 😬",
    "Missed something there, say it again 🙃",
    "Facing a technical glitch 😑",
    "I can't respond properly right now 😪",
    "There's some internal error 🫠",
    "System might be overloaded 😴",
    "Seems like a connection issue 😌",
    "I'm a little confused right now 🥺",
    "There was a problem during processing 😵",
    "I'm not functioning properly at the moment 😤",
    "Ran into an unexpected error 🫤",
    "Restarting myself, please wait 😔",
    "Dealing with some technical difficulties 💗"
]
