import pandas as pd
import requests
import numpy as np
import seaborn as sns
import json
import dataframe_image
import os

base_url = "https://api.open-meteo.com/v1/forecast?"

with open("secrets.json") as f:
    cfg = json.load(f)

lat = cfg["lat"]
lon = cfg["lon"]
telegram_key = cfg["telegram_key"]
telegram_chatid = cfg["telegram_chatid"]


weather_params = {
    "latitude": lat,
    "longitude": lon,
    "hourly": [
        "temperature_2m",
        "relativehumidity_2m",
        "weathercode",
        "rain",
        "windspeed_10m",
        "apparent_temperature",
        "cloudcover",
    ],
    "start_date": pd.to_datetime("now", utc=True).strftime("%F"),
    "end_date": (pd.to_datetime("now", utc=True) + pd.Timedelta("5 days")).strftime(
        "%F"
    ),
    "windspeed_unit": "ms",
    "precipitation_unit": "mm",
    "temperature_unit": "celsius",
    "current_weather": True,
}

units = {
    "rain": "mm",
    "temperature_2m": "C",
    "apparent_temperature": "C",
    "relativehumidity_2m": "%",
    "windspeed_10m": "m/s",
    "cloudcover": "%",
}

wmo_weather_codes = [
    ([0], "Clear sky"),
    ([0], "Mainly clear"),
    ([2], "partly cloudy"),
    ([3], "overcast"),
    ([45, 48], "Fog"),
    ([51], "Light drizzle"),
    ([53], "Moderate drizzle"),
    ([55], "Intense drizzle"),
    ([56, 57], "Freezing Drizzle"),
    ([61], "Slight rain"),
    ([63], "Moderate rain"),
    ([65], "Heavy rain"),
    ([66, 67], "Freezing Rain"),
    ([71, 73, 75], "Snow fall"),
    ([77], "Snow grains"),
    ([80], "Slight showers"),
    ([81], "Moderate showers"),
    ([82], "Violent showers"),
    ([85, 86], "Snow showers"),
    ([95], "Thunderstorm"),
    ([96, 99], "Thunderstorm with hail"),
]


def get_weather():
    response = requests.get(base_url, params=weather_params)
    data = response.json()

    current_weather = data["current_weather"]
    for (codes, description) in wmo_weather_codes:
        if current_weather["weathercode"] in codes:
            current_weather["description"] = description
            del current_weather["weathercode"]
            break

    hourly_weather = (
        pd.DataFrame(data["hourly"]).set_index("time").drop(columns=["weathercode"])
    )
    hourly_weather.index = pd.to_datetime(hourly_weather.index, utc=True)
    hourly_weather = hourly_weather.sort_index().loc[
        hourly_weather.index > pd.to_datetime("now", utc=True)
    ]
    return current_weather, hourly_weather


def style_hourly_weather(hourly_weather):

    # Reshape
    hourly_weather = hourly_weather[
        ["temperature_2m", "rain", "windspeed_10m", "cloudcover"]
    ].rename(
        columns={
            "temperature_2m": "T",
            "rain": "Rain",
            "windspeed_10m": "Wind",
            "cloudcover": "Clouds",
        }
    )

    hourly_weather = hourly_weather.head(24).iloc[::2, :].T
    hourly_weather.columns = [x.strftime("%H:%M") for x in hourly_weather.columns]

    ## Prep colors
    create_bounds = lambda x: [(x[i], x[i + 1]) for i in range(len(x) - 1)]

    temp_bounds = create_bounds([-np.inf, 0, 5, 10, 15, 20, 25, np.inf])
    wind_bounds = create_bounds([-np.inf, 2, 5, 7, 10, 12, 15, np.inf])
    cloud_bounds = create_bounds([-np.inf, 1, 20, 40, 60, 90, 100, np.inf])

    cloud_palette = sns.color_palette(
        "gist_gray_r", n_colors=len(cloud_bounds)
    ).as_hex()

    temp_palette = sns.color_palette("Spectral", n_colors=len(temp_bounds)).as_hex()
    temp_palette.reverse()
    wind_palette = sns.cubehelix_palette(
        start=0.5, rot=-0.75, gamma=0.7, hue=2, n_colors=len(wind_bounds)
    ).as_hex()

    ## Style
    styler = hourly_weather.style
    styler.set_properties(
        **{
            "text-align": "center",
        }
    )
    styler = styler.set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("text-align", "center"),
                    # ('color', 'white'),
                ],
            }
        ]
    )

    def apply_colors(value, text_color, bounds, palette):
        idx = [
            i
            for i, bound in enumerate(bounds)
            if value >= bound[0] and value < bound[1]
        ][0]
        return f"color:{text_color};background-color:{palette[idx]}"

    styler = styler.applymap(
        apply_colors,
        text_color="white",
        bounds=cloud_bounds,
        palette=cloud_palette,
        subset=(["Clouds"], slice(None)),
    )
    styler = styler.applymap(
        apply_colors,
        text_color="black",
        bounds=temp_bounds,
        palette=temp_palette,
        subset=(["T"], slice(None)),
    )
    styler = styler.applymap(
        apply_colors,
        text_color="black",
        bounds=wind_bounds,
        palette=wind_palette,
        subset=(["Wind"], slice(None)),
    )

    styler = styler.bar(
        subset=(["Rain"], slice(None)),
        color="#3498d6",
        props="width: 1em;",
        vmin=0,
        vmax=5,
        align="mid",
    )
    # styler = styler.bar(subset=(['Wind'], slice(None)), cmap=sns.color_palette("crest", as_cmap=True, n_colors=10), props="width: 1em;", vmin=0, vmax=15, align='mid')

    styler = styler.format(precision=1)
    return styler


def run():

    current, hourly = get_weather()

    caption = f"Currently {current['description']}, {current['temperature']}℃."
    extras = []

    if hourly.head(10)["rain"].gt(0).any():
        extras.append("rain")
    if hourly.head(10)["rain"].gt(8).any():
        extras.append("be windy")
    if extras:
        caption += ". It's going to " + " and ".join(extras) + "."

    caption += "\n" + hourly.head(12)["temperature_2m"].agg(
        {"H:": "max", "L:": "min"}
    ).astype(str).apply(lambda x: x + "℃").to_string().replace(" ", "").replace(
        "\n", ", "
    )

    styler = style_hourly_weather(hourly)

    # need headless chromium to keep formatting
    dataframe_image.export(
        styler,
        "weather.png",
    )  # table_conversion="matplotlib"
    files = {"photo": open("weather.png", "rb")}

    telegram_params = {
        "chat_id": telegram_chatid,
        "disable_notification": False,
        "caption": caption,
    }

    r = requests.post(
        f"https://api.telegram.org/bot{telegram_key}/sendPhoto",
        params=telegram_params,
        files=files,
    )

    return {"statusCode": r.status_code, "body": r.json()}


run()
