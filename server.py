from flask import Flask, jsonify
from flask_cors import CORS
import math
import pandas as pd

from snowflake_util import get_connector, get_after


app = Flask(__name__)
CORS(app)


def nan_to_none(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, float) and math.isnan(value):
            dictionary[key] = None
    return dictionary


print("Prefetching wells data...")
print("=" * 50)
con = get_connector()
df = get_after(con)
print("Done prefetching wells data.")
print("=" * 50)
print(df.head())
df_dict = df.to_dict(orient="records")
df_dict = [nan_to_none(record) for record in df_dict]


@app.route("/api/wells", methods=["GET"])
def get_wells():
    return jsonify(df_dict)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
