<script setup lang="ts">
import axios from "axios";
import { ref, reactive, computed, watch } from "vue";
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
  facet_row: '',
  size: 6,
  opacity: 0.8,
  colorPalette: ''
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
const handleRemoveNA = async (columns: string[]) => {
  try {
    error.value = null; // エラーメッセージをクリア
    const response = await axios.post(endpoint + "/remove_na", { columns }); // サーバーにNA値削除をリクエスト
    updateTableState(response.data); // レスポンスデータでテーブルの状態を更新
  } catch (error) {
    console.error("Remove NA error:", error);
    error.value = "Error removing NA values"; // エラーメッセージを設定
  }
};

// 指定した値の範囲でフィルタリングする処理
const handleFilterByValue = async (column: string, values: any[]) => {
  try {
    error.value = null; // エラーメッセージをクリア
    const response = await axios.post(endpoint + "/filter_by_value", { column, values }); // サーバーにフィルタをリクエスト
    updateTableState(response.data); // レスポンスデータでテーブルの状態を更新
  } catch (error) {
    console.error("Filter by value error:", error);
    error.value = "Error filtering by value"; // エラーメッセージを設定
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
    const response = await axios.post(endpoint + "/plot_scatter", {
      ...plotSettings,
      size: Number(plotSettings.size),
      opacity: Number(plotSettings.opacity)
    }); // プロット設定をサーバーに送信
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
  plotSettings.size = 6;
  plotSettings.opacity = 0.8;
  plotSettings.colorPalette = '';
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
  return selected ? { backgroundColor: 'lightblue', color: '#4d4d4d' } : { backgroundColor: 'white', color: '#4d4d4d' };
};

// カラーパレットの選択肢
const colorPalettes = ['Default', 'jet', 'RdBu', 'RdBu_r', 'Blues', 'Reds', 'Greens'];

// カラムのユニーク値または数値範囲を取得する関数
const columnValues = ref<any[]>([]);
const selectedRemoveNAColumn = ref<string | null>(null);
const selectedFilterColumn = ref<string | null>(null);
const selectedFilterValues = ref<any[]>([]);

watch(selectedFilterColumn, async (newColumn) => {
  if (newColumn) {
    try {
      const response = await axios.post(endpoint + "/get_column_values", { column: newColumn });
      columnValues.value = response.data.values;
      selectedFilterValues.value = [];
    } catch (error) {
      console.error("Error fetching column values:", error);
      error.value = "Error fetching column values"; // エラーメッセージを設定
    }
  } else {
    columnValues.value = [];
  }
});

const toggleSelection = (value: any) => {
  const index = selectedFilterValues.value.indexOf(value);
  if (index === -1) {
    selectedFilterValues.value.push(value);
  } else {
    selectedFilterValues.value.splice(index, 1);
  }
};
</script>

<template>
  <div class="container">
    <!-- ヘッダーエリア -->
    <header class="header">
      <div class="header-left">
        <input type="file" @change="handleFileChange" />
        <button type="button" @click="handleUpload">Upload CSV</button>
        <div v-if="tableState.data.length > 0 && tableState.headers.length > 0" class="table-info">
          <p>Columns: {{ tableState.headers.length }}, Rows: {{ tableState.data.length }}</p>
        </div>
      </div>
    </header>

    <!-- エラーメッセージの表示 -->
    <p v-if="error" style="color: red;">{{ error }}</p>

    <!-- データ表示とプロットエリア -->
    <div class="split-view">
      <div class="left-view">
        <!-- 前処理エリア -->
        <div class="preprocessing-controls">
          <h3>Data Preprocessing</h3>
          <div>
            <label>
              Remove NAs from:
              <select v-model="selectedRemoveNAColumn" :style="dropdownStyle(selectedRemoveNAColumn)">
                <option value="">All Columns</option>
                <option v-for="header in tableState.headers" :key="header" :value="header">{{ header }}</option>
              </select>
            </label>
            <button type="button" @click="handleRemoveNA(selectedRemoveNAColumn ? [selectedRemoveNAColumn] : [])">Remove NA</button>
          </div>
          <div class="filter-by-value">
            <div class="filter-left">
              <label>
                Filter by value:
                <select v-model="selectedFilterColumn" :style="dropdownStyle(selectedFilterColumn)">
                  <option value="">Select Column</option>
                  <option v-for="header in tableState.headers" :key="header" :value="header">{{ header }}</option>
                </select>
              </label>
              <button type="button" @click="handleFilterByValue(selectedFilterColumn, selectedFilterValues)">Filter</button>
            </div>
            <div class="filter-right">
              <label v-if="typeof columnValues[0] === 'number'">
                Range:
                <input type="number" v-model.number="columnValues[0]" :style="dropdownStyle(columnValues[0] === null ? '' : columnValues[0].toString())" />
                to
                <input type="number" v-model.number="columnValues[1]" :style="dropdownStyle(columnValues[1] === null ? '' : columnValues[1].toString())" />
              </label>
              <label v-else>
                Values:
                <div class="multiselect-container">
                  <div v-for="value in columnValues" :key="value" @click="toggleSelection(value)" :class="{'selected': selectedFilterValues.includes(value)}" :style="dropdownStyle(selectedFilterValues.includes(value) ? value.toString() : '')">
                    {{ value }}
                  </div>
                </div>
              </label>
            </div>
          </div>
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
        <div style="margin-top: 30px;" v-if="tableState.dataDescribed.length > 0 && tableState.headersDescribed.length > 0" class="table-container">
          <table>
            <thead>
              <tr>
                <th class="sticky-column">
                  <div class="header-cell">ColumnName</div>
                </th>
                <th v-for="header in tableState.headersDescribed.slice(1)" :key="header">
                  <div class="header-cell">{{ header }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in tableState.dataDescribed" :key="rowIndex">
                <td class="sticky-column">
                  {{ row['ColumnName'] }}
                </td>
                <td v-for="header in tableState.headersDescribed.slice(1)" :key="header">
                  {{ row[header] === null ? '-' : row[header] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="right-view">
        <!-- 散布図プロットの設定 -->
        <div class="plot-controls">
          <div class="plot-settings-row">
            <button type="button" @click="resetPlotSettings" class="reset-button">Reset</button>
          </div>
          <div class="plot-settings-row">
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
            <label>
              Color:
              <select v-model="plotSettings.color" :style="dropdownStyle(plotSettings.color)">
                <option value="">Select Color</option>
                <option v-for="header in tableState.headers" :key="header" :value="header">{{ header }}</option>
              </select>
            </label>
            <label>
              Color Palette:
              <select v-model="plotSettings.colorPalette" :disabled="!plotSettings.color" :style="dropdownStyle(plotSettings.colorPalette)">
                <option value="">Select Color Palette</option>
                <option v-for="palette in colorPalettes" :key="palette" :value="palette">{{ palette }}</option>
              </select>
            </label>
          </div>
          <div class="plot-settings-row">
            <label>
              Size:
              <input type="range" v-model="plotSettings.size" min="1" max="20" step="1">
            </label>
            <label>
              Transparency:
              <input type="range" v-model="plotSettings.opacity" min="0.1" max="1" step="0.1">
            </label>
          </div>
          <div class="plot-settings-row">
            <button type="button" @click="handlePlot" class="plot-button">Scatter Plot</button>
          </div>
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

/* ヘッダーエリアのスタイル */
.header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-bottom: 20px;
}

/* ヘッダー左部分のスタイル */
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* コントロールエリアのスタイル */
.controls {
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
  font-size: 14px;
  text-align: left;
}

/* テーブルコンテナのスタイル */
.table-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #000;
  margin-bottom: 30px;
}

table {
  width: 100%;
  border-collapse: collapse;
  background-color: #ffffff;
}

th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
  color: #333;
  font-size: 12px;
}

thead {
  position: sticky;
  top: 0;
  background-color: #f2f2f2;
  z-index: 1;
}

tr:nth-child(even) {
  background-color: #f9f9f9;
}

.header-cell {
  white-space: pre-wrap;
  word-wrap: break-word;
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
  border: 1px solid #ddd; 
  background-color: white; 
  color: #4d4d4d;
}

.plot-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.plot-settings-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.plot-settings-row label {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.plot-settings-row input[type="range"] {
  margin-top: 5px;
}

.reset-button {
  margin-left: auto;
}

.plot-button {
  background-color: #007bff;
  color: white;
  font-size: 16px;
  padding: 10px 20px;
  margin: 0 auto;
  display: block;
}

.split-view {
  display: flex;
  height: calc(100vh - 100px);
}

.resizable-divider {
  width: 5px;
  cursor: ew-resize;
  background-color: #ccc;
  position: relative;
}

.resizable-divider:after {
  content: '';
  display: block;
  height: 100%;
  width: 100%;
  position: absolute;
  left: 0;
  top: 0;
}

.left-view, .right-view {
  overflow: auto;
  padding: 10px;
  box-sizing: border-box;
}

.left-view {
  flex: 4;
  border-right: 1px solid #ddd;
}

.right-view {
  flex: 6;
  display: flex;
  flex-direction: column;
}

.plot-container {
  flex: 1;
  margin-top: 20px;
}

.sticky-column {
  position: sticky;
  left: 0;
  background-color: #f2f2f2;
  z-index: 2;
}

/* 前処理コントロールのスタイル */
.preprocessing-controls {
  margin-bottom: 20px;
}

.preprocessing-controls h3 {
  margin-bottom: 10px;
}

.preprocessing-controls div {
  margin-bottom: 10px;
}

.filter-by-value {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
  max-width: 600px;
  height: 150px; /* 固定サイズに設定 */
  border: 1px solid #ddd;
  padding: 10px;
}

.filter-left {
  flex: 1;
}

.filter-right {
  flex: 1;
  overflow-y: auto;
  height: 100%;
}

.multiselect-container {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.multiselect-container div {
  padding: 5px;
  border: 1px solid #ddd;
  background-color: white;
  cursor: pointer;
}

.multiselect-container div.selected {
  background-color: lightblue;
}
</style>
