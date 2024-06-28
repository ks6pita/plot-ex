from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__, static_folder="dist", static_url_path="")
CORS(app)

original_df = None

def describing(df):
    # 欠損値の情報を計算
    missing_values_df = df.isnull().sum().reset_index()
    missing_values_df.columns = ['ColumnName', 'MissingValues']

    # 各カラムの統計情報を計算
    stats_df = df.describe(include='all').transpose().reset_index()
    stats_df.columns = ['ColumnName'] + list(stats_df.columns[1:])

    # 有効数字を4にフォーマット
    def format_sigfig(value, sigfig=4):
        if pd.notnull(value):
            return f"{value:.{sigfig}g}"
        return value

    stats_df['mean'] = stats_df['mean'].apply(format_sigfig)
    stats_df['std'] = stats_df['std'].apply(format_sigfig)

    # 欠損値情報と統計情報をマージ
    merged_df = pd.merge(missing_values_df, stats_df, on='ColumnName', how='left')

    # データ型情報のDataFrame作成
    dtypes_df = pd.DataFrame(df.dtypes).reset_index()
    dtypes_df.columns = ['ColumnName', 'DataType']
    dtypes_df['DataType'] = dtypes_df['DataType'].astype(str)  # データ型を文字列に変換

    # マージしてデータ型情報を追加
    final_df = pd.merge(merged_df, dtypes_df, on='ColumnName', how='left')
    
    column_order = ['ColumnName', 'DataType', 'count', 'MissingValues', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', 'unique', 'top', 'freq']
    final_df = final_df[column_order]

    return final_df

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    global original_df
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        try:
            # オリジナルのデータフレームを読み込む
            original_df = pd.read_csv(file)
            described_df = describing(original_df)
            
            # Vue.jsに送信するために、新しいデータフレームを作成してNaNを変換
            df_to_json = original_df.replace({np.nan: None})
            described_df_to_json = described_df.replace({np.nan: None})
            
            # データフレームをVue.jsで使いやすい形式に変換
            data = {
                "headers": df_to_json.columns.tolist(),
                "data": df_to_json.to_dict(orient='records'),
                "headers_described": described_df_to_json.columns.tolist(),
                "data_described": described_df_to_json.to_dict(orient='records')
            }
            
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/remove_na", methods=["POST"])
def remove_na():
    global original_df
    if original_df is None:
        return jsonify({"error": "No data uploaded yet"}), 400
    
    # NA値を削除した新しいデータフレームを作成
    processed_df = original_df.dropna()
    described_prcd_df = describing(processed_df)

    # Vue.jsに送信するために、新しいデータフレームを作成してNaNを変換
    df_to_json = processed_df.replace({np.nan: None})
    described_df_to_json = described_prcd_df.replace({np.nan: None})

    
    # データフレームをVue.jsで使いやすい形式に変換
    data = {
        "headers": df_to_json.columns.tolist(),
        "data": df_to_json.to_dict(orient='records'),
        "headers_described": described_df_to_json.columns.tolist(),
        "data_described": described_df_to_json.to_dict(orient='records')
    }
    
    return jsonify(data)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
