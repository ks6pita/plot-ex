from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
import plotly.express as px
import json
import plotly

app = Flask(__name__, static_folder="dist", static_url_path="")
CORS(app)

original_df = None
processed_df = None  # NAを除去したデータを保持するための変数

def describing(df):
    missing_values_df = df.isnull().sum().reset_index()
    missing_values_df.columns = ['ColumnName', 'MissVal']
    stats_df = df.describe(include='all').transpose().reset_index()
    stats_df.columns = ['ColumnName'] + list(stats_df.columns[1:])
    def format_sigfig(value, sigfig=4):
        if pd.notnull(value):
            return f"{value:.{sigfig}g}"
        return value
    stats_df['mean'] = stats_df['mean'].apply(format_sigfig)
    stats_df['std'] = stats_df['std'].apply(format_sigfig)
    merged_df = pd.merge(missing_values_df, stats_df, on='ColumnName', how='left')
    dtypes_df = pd.DataFrame(df.dtypes).reset_index()
    dtypes_df.columns = ['ColumnName', 'Type']
    dtypes_df['Type'] = dtypes_df['Type'].astype(str)
    final_df = pd.merge(merged_df, dtypes_df, on='ColumnName', how='left')
    column_order = ['ColumnName', 'Type', 'count', 'Miss', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', 'unique', 'top', 'freq']
    final_df = final_df.reindex(columns=column_order)
    final_df.columns = ['ColumnName', 'Type', 'Rows', 'Miss', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', 'unique', 'top', 'freq']
    return final_df

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    global original_df, processed_df
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        try:
            original_df = pd.read_csv(file)
            processed_df = original_df.copy()  # 初期状態はオリジナルデータ
            described_df = describing(original_df)
            df_to_json = original_df.replace({np.nan: None})
            described_df_to_json = described_df.replace({np.nan: None})
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
    global original_df, processed_df
    if original_df is None:
        return jsonify({"error": "No data uploaded yet"}), 400
    processed_df = original_df.dropna()
    described_prcd_df = describing(processed_df)
    df_to_json = processed_df.replace({np.nan: None})
    described_df_to_json = described_prcd_df.replace({np.nan: None})
    data = {
        "headers": df_to_json.columns.tolist(),
        "data": df_to_json.to_dict(orient='records'),
        "headers_described": described_df_to_json.columns.tolist(),
        "data_described": described_df_to_json.to_dict(orient='records')
    }
    return jsonify(data)

@app.route("/plot_scatter", methods=["POST"])
def plot_scatter():
    global processed_df
    if processed_df is None:
        return jsonify({"error": "No processed data available"}), 400
    
    request_data = request.json
    x = request_data.get('x')
    y = request_data.get('y')
    color = request_data.get('color', None)
    facet_col = request_data.get('facet_col', None)
    facet_row = request_data.get('facet_row', None)
    symbol = request_data.get('symbol', None)
    size = request_data.get('size', 6)
    opacity = request_data.get('opacity', 0.8)
    
    if not x or not y:
        return jsonify({"error": "x and y axis must be specified"}), 400
    
    try:
        plot_params = {
            'x': x,
            'y': y,
            'data_frame': processed_df
        }
        if color:
            plot_params['color'] = color
        if facet_col:
            plot_params['facet_col'] = facet_col
        if facet_row:
            plot_params['facet_row'] = facet_row
        if symbol:
            plot_params['symbol'] = symbol
        
        fig = px.scatter(**plot_params)
        fig.update_traces(marker=dict(size=size, opacity=opacity))
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return jsonify(graph_json)
    except Exception as e:
        error_message = f"Error in plot_scatter: {str(e)}"
        print(error_message)  # Flaskサーバーのコンソールにエラーメッセージを表示
        return jsonify({"error": error_message}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
