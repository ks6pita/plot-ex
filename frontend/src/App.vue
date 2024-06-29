<script setup lang="ts">
import axios from "axios";
import { ref, reactive, computed } from "vue";
import Plotly from "plotly.js-dist-min";

// APIエンドポイントの設定
const endpoint = import.meta.env.VITE_API_ENDPOINT as string;

// ファイル選択用のref
const csvFile = ref<File | null>(null);

// テーブルの状態管理
const tableState = reactive({
  headers: [] as string[], // データテーブルのヘッダー
  data: [] as Record<string, any>[], // データテーブルのデータ
  headersDescribed: [] as string[], // describedテーブルのヘッダー
  dataDescribed: [] as Record<string, any>[] // describedテーブルのデータ
});

// エラーメッセージの管理
const error = ref<string | null>(null);

// describeテーブルのカラム名の翻訳
const translateHeaders = (headers: string[]) => {
  return headers.map(header => {
    if (header === 'count') return 'Rows';
    if (header === 'MissingValues') return 'MissVal';
    if (header === 'DataType') return 'Type';
    return header;
  });
};

// グラフの描画設定
const plotSettings = reactive({
  x: '',
  y: '',
  color: '',
  facet_col: '',
  facet_row: ''
});

// プロット用のref
const plotRef = ref<HTMLElement | null>(null);

// ファイルが変更されたときの処理
const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    csvFile.value = target.files[0]; // 選択されたファイルをrefに設定
  }
};

// CSVファイルをアップロードする処理
const handleUpload = async () => {
  if (!csvFile.value) return;

  const formData = new FormData();
  formData.append("file", csvFile.value); // ファイルをFormDataに追加

  try {
    error.value = null; // エラーメッセージをクリア
    const response = await axios.post(endpoint + "/upload_csv", formData); // ファイルをサーバーにアップロード
    updateTableState(response.data); // レスポンスデータでテーブルの状態を更新
  } catch (error) {
    console.error("Upload error:", error);
    error.value = "Error uploading file"; // エラーメッセージを設定
  }
};

// NA値を削除する処理
const handleRemoveNA = async () => {
  try {
    error.value = null; // エラーメッセージをクリア
    const response = await axios.post(endpoint + "/remove_na"); // サーバーにNA値削除をリクエスト
    updateTableState(response.data); // レスポンスデータでテーブルの状態を更新
  } catch (error) {
    console.error("Remove NA error:", error);
    error.value = "Error removing NA values"; // エラーメッセージを設定
  }
};

// 散布図をプロットする処理
const handlePlot = async () => {
  if (!plotSettings.x || !plotSettings.y) {
    error.value = "Please select both x and y axes";
    return;
  }
  try {
    error.value = null; // エラーメッセージをクリア
    const response = await axios.post(endpoint + "/plot_scatter", plotSettings); // プロット設定をサーバーに送信
    const plotData = JSON.parse(response.data);
    Plotly.newPlot(plotRef.value, plotData.data, plotData.layout);
  } catch (error) {
    console.error("Plot error:", error);
    error.value = "Error generating plot"; // エラーメッセージを設定
  }
};

// 散布図の設定をリセットする関数
const resetPlotSettings = () => {
  plotSettings.x = '';
  plotSettings.y = '';
  plotSettings.color = '';
  plotSettings.facet_col = '';
  plotSettings.facet_row = '';
};

// テーブルの状態を更新する関数
const updateTableState = (data: any) => {
  if (data && data.headers && Array.isArray(data.data) && data.headers_described && Array.isArray(data.data_described)) {
    tableState.headers = ['index', ...data.headers]; // インデックス列を追加したヘッダーを設定
    tableState.data = data.data.map((row, index) => ({ index, ...row })); // 各行にインデックスを追加
    tableState.headersDescribed = translateHeaders(data.headers_described); // describedテーブルのヘッダーを設定
    tableState.dataDescribed = data.data_described; // describedテーブルのデータを設定
  } else {
    error.value = "Unexpected response structure"; // エラーメッセージを設定
    console.error("Unexpected response structure:", data);
  }
  console.log("Table Headers:", tableState.headers);
  console.log("Table Data:", tableState.data);
  console.log("Described Table Headers:", tableState.headersDescribed);
  console.log("Described Table Data:", tableState.dataDescribed);
};

// 数値型以外のカラムを取得する関数
const getNonNumericColumns = computed(() => {
  return tableState.headers.filter(header => {
    const columnData = tableState.data.map(row => row[header]);
    return columnData.every(value => isNaN(value) || value === null);
  });
});

// 選択されたパラメータに応じてドロップダウンの背景色を変更する関数
const dropdownStyle = (selected: string) => {
  return selected ? { backgroundColor: 'lightblue' } : {};
};

</script>

<template>
  <div class="container">
    <div class="controls">
      <!-- ファイル選択用のインプット -->
      <input type="file" @change="handleFileChange" />
      <!-- CSVファイルアップロードボタン -->
      <button type="button" @click="handleUpload">Upload CSV</button>
      <!-- NA値削除ボタン -->
      <button type="button" @click="handleRemoveNA">Remove NA</button>
    </div>
    
    <!-- エラーメッセージの表示 -->
    <p v-if="error" style="color: red;">{{ error }}</p>
    
    <!-- データ表示とプロットエリア -->
    <div class="split-view">
      <div class="left-view">
        <!-- オリジナルデータテーブルの情報表示 -->
        <div v-if="tableState.data.length > 0 && tableState.headers.length > 0" class="table-info">
          <p>Original Data - Columns: {{ tableState.headers.length }}, Rows: {{ tableState.data.length }}</p>
        </div>

        <!-- オリジナルデータテーブルの表示 -->
        <div class="table-container" v-if="tableState.data.length > 0 && tableState.headers.length > 0">
          <table>
            <thead>
              <tr>
                <th v-for="header in tableState.headers" :key="header">
                  <div class="header-cell">{{ header }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in tableState.data" :key="rowIndex">
                <td v-for="header in tableState.headers" :key="header">
                  {{ row[header] === null ? 'N/A' : row[header] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- describedテーブルの表示 -->
        <div style="margin-top: 30px;" v-if="tableState.dataDescribed.length > 0 && tableState.headersDescribed.length > 0">
          <table>
            <thead>
              <tr>
                <th v-for="header in tableState.headersDescribed" :key="header">
                  <div class="header-cell">{{ header }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in tableState.dataDescribed" :key="rowIndex">
                <td v-for="header in tableState.headersDescribed" :key="header">
                  {{ row[header] === null ? '-' : row[header] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="right-view">
        <!-- 散布図プロットの設定 -->
        <div class="plot-settings">
          <label>
            X Axis:
            <select v-model="plotSettings.x" :style="dropdownStyle(plotSettings.x)">
              <option value="">Select X Axis</option>
              <option v-for="header in tableState.headers" :key="header" :value="header">{{ header }}</option>
            </select>
          </label>
          <label>
            Y Axis:
            <select v-model="plotSettings.y" :style="dropdownStyle(plotSettings.y)">
              <option value="">Select Y Axis</option>
              <option v-for="header in tableState.headers" :key="header" :value="header">{{ header }}</option>
            </select>
          </label>
          <label>
            Color:
            <select v-model="plotSettings.color" :style="dropdownStyle(plotSettings.color)">
              <option value="">Select Color</option>
              <option v-for="header in tableState.headers" :key="header" :value="header">{{ header }}</option>
            </select>
          </label>
          <label>
            Facet Column:
            <select v-model="plotSettings.facet_col" :style="dropdownStyle(plotSettings.facet_col)">
              <option value="">Select Facet Column</option>
              <option v-for="header in getNonNumericColumns" :key="header" :value="header">{{ header }}</option>
            </select>
          </label>
          <label>
            Facet Row:
            <select v-model="plotSettings.facet_row" :style="dropdownStyle(plotSettings.facet_row)">
              <option value="">Select Facet Row</option>
              <option v-for="header in getNonNumericColumns" :key="header" :value="header">{{ header }}</option>
            </select>
          </label>
          <button type="button" @click="handlePlot">Plot Scatter</button>
          <button type="button" @click="resetPlotSettings">Reset</button>
        </div>
        
        <!-- プロットエリア -->
        <div ref="plotRef" class="plot-container"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* コンテナのスタイル */
.container {
  padding: 20px;
}

/* コントロールエリアのスタイル */
.controls {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

/* ボタンのスタイル */
button {
  background-color: grey;
  border: black;
  color: black;
  padding: 10px 20px;
  text-align: center;
  text-decoration: none;
  font-size: 12px;
  margin: 4px 2px;
  cursor: pointer;
  border-radius: 4px;
}

/* ファイル入力のスタイル */
input[type="file"] {
  margin-right: 10px;
}

/* テーブル情報のスタイル */
.table-info {
  margin-bottom: 10px;
  font-size: 14px;
}

/* テーブルコンテナのスタイル */
.table-container {
  max-height: 400px; /* テーブルの最大高さを設定 */
  overflow-y: auto; /* 垂直スクロールを有効にする */
  border: 1px solid #000; /* テーブルの境界線 */
  margin-bottom: 30px; /* テーブル間のスペースを追加 */
}

/* テーブルのスタイル */
table {
  width: 100%; /* テーブルの幅を100%に設定 */
  border-collapse: collapse; /* 境界線を重ならないようにする */
  background-color: #ffffff; /* テーブルの背景色 */
}

/* テーブルヘッダーとセルのスタイル */
th, td {
  border: 1px solid #ddd; /* セルの境界線 */
  padding: 8px; /* セルの内側余白 */
  text-align: left; /* テキストを左揃え */
  color: #333; /* テキストの色 */
  font-size: 12px; /* テキストのフォントサイズ */
}

/* テーブルヘッダーのスタイル */
thead {
  position: sticky; /* ヘッダーを固定 */
  top: 0; /* ヘッダーをテーブルの上部に固定 */
  background-color: #f2f2f2; /* ヘッダーの背景色 */
  z-index: 1; /* ヘッダーの重なり順序 */
}

/* 偶数行の背景色を変更 */
tr:nth-child(even) {
  background-color: #f9f9f9;
}

/* ヘッダーセルのスタイル */
.header-cell {
  white-space: pre-wrap; /* 折り返しを有効にしてセル内で折り返し */
  word-wrap: break-word; /* 長い単語を折り返し */
}

/* プロット設定のスタイル */
.plot-settings {
  margin-bottom: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px;
  border: 1px solid #ddd;
}
.plot-settings label {
  display: flex;
  flex-direction: column;
}
.plot-settings select {
  margin-top: 5px;
  padding: 5px;
  font-size: 14px;
  border: 1px solid #ddd; /* ボックスの枠を追加 */
  background-color: #ffffff; /* デフォルトの背景色に戻す */
  color: #333;
}

/* Split viewのスタイル */
.split-view {
  display: flex;
  height: calc(100vh - 100px); /* コントロールエリアの高さを引いた高さを設定 */
}

.left-view {
  flex: 4;
  overflow: auto;
  padding: 10px;
  border-right: 1px solid #ddd;
  box-sizing: border-box;
}

.right-view {
  flex: 6;
  overflow: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  box-sizing: border-box;
}

/* プロットエリアのスタイル */
.plot-container {
  flex: 1;
  margin-top: 20px;
}
</style>
