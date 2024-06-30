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
  padding: 20px; /* コンテナのパディング */
}

/* ヘッダーエリアのスタイル */
.header {
  display: flex; /* ヘッダーのフレックスボックス設定 */
  align-items: center; /* ヘッダーのアイテムを中央に揃える */
  justify-content: flex-start; /* ヘッダーのアイテムを左揃えにする */
  margin-bottom: 20px; /* ヘッダーの下部マージン */
}

/* ヘッダー左部分のスタイル */
.header-left {
  display: flex; /* ヘッダー左部分のフレックスボックス設定 */
  align-items: center; /* ヘッダー左部分のアイテムを中央に揃える */
  gap: 10px; /* ヘッダー左部分のアイテム間のギャップ */
}

/* コントロールエリアのスタイル */
.controls {
  display: flex; /* コントロールエリアのフレックスボックス設定 */
  gap: 10px; /* コントロールエリアのアイテム間のギャップ */
}

/* ボタンのスタイル */
button {
  background-color: grey; /* ボタンの背景色 */
  border: black; /* ボタンの境界線色 */
  color: black; /* ボタンの文字色 */
  padding: 2px 10px; /* ボタンのパディング */
  text-align: center; /* ボタンのテキストを中央揃え */
  text-decoration: none; /* ボタンのテキスト装飾をなしにする */
  font-size: 14px; /* ボタンのフォントサイズ */
  margin: 2px 2px; /* ボタンのマージン */
  cursor: pointer; /* ボタンのカーソルをポインターにする */
  border-radius: 4px; /* ボタンの角を丸くする */
}

/* ファイル入力のスタイル */
input[type="file"] {
  margin-right: 10px; /* ファイル入力の右マージン */
}

/* テーブル情報のスタイル */
.table-info {
  font-size: 14px; /* テーブル情報のフォントサイズ */
  text-align: left; /* テーブル情報のテキストを左揃え */
}

/* テーブルコンテナのスタイル */
.table-container {
  max-height: 400px; /* テーブルコンテナの最大高さ */
  overflow-y: auto; /* テーブルコンテナの縦方向のオーバーフローを自動にする */
}

/* ドロップダウンのスタイル */
select {
  padding: 5px; /* ドロップダウンのパディング */
  margin: 5px; /* ドロップダウンのマージン */
  border-radius: 4px; /* ドロップダウンの角を丸くする */
}

/* プロットボタンのスタイル */
.plot-button {
  background-color: #4CAF50; /* プロットボタンの背景色 */
  color: white; /* プロットボタンの文字色 */
  padding: 10px 24px; /* プロットボタンのパディング */
  border: none; /* プロットボタンの境界線をなしにする */
  border-radius: 4px; /* プロットボタンの角を丸くする */
  cursor: pointer; /* プロットボタンのカーソルをポインターにする */
}

/* プロットコンテナのスタイル */
.plot-container {
  width: 100%; /* プロットコンテナの幅を100%にする */
  height: 500px; /* プロットコンテナの高さを500pxにする */
  /* border: 1px solid #ccc; プロットコンテナの境界線 */
  margin-top: 20px; /* プロットコンテナの上部マージン */
}
/* ボタンのスタイル */
button {
  background-color: grey; /* ボタンの背景色 */
  border: black; /* ボタンの境界線 */
  color: black; /* ボタンの文字色 */
  padding: 10px 20px; /* ボタンのパディング */
  text-align: center; /* ボタンのテキストを中央揃え */
  text-decoration: none; /* ボタンのテキスト装飾をなしにする */
  font-size: 12px; /* ボタンのフォントサイズ */
  margin: 4px 2px; /* ボタンのマージン */
  cursor: pointer; /* ボタンのカーソルをポインターにする */
  border-radius: 4px; /* ボタンの角を丸くする */
}

/* ファイル入力のスタイル */
input[type="file"] {
  margin-right: 10px; /* ファイル入力の右マージン */
}

/* テーブル情報のスタイル */
.table-info {
  font-size: 14px; /* テーブル情報のフォントサイズ */
  text-align: left; /* テーブル情報のテキストを左揃え */
}

/* テーブルコンテナのスタイル */
.table-container {
  max-height: 400px; /* テーブルコンテナの最大高さ */
  overflow-y: auto; /* テーブルコンテナの縦方向のオーバーフローを自動にする */
}

/* ドロップダウンのスタイル */
select {
  padding: 5px; /* ドロップダウンのパディング */
  margin: 5px; /* ドロップダウンのマージン */
  border-radius: 4px; /* ドロップダウンの角を丸くする */
}

/* プロットボタンのスタイル */
.plot-button {
  background-color: #4CAF50; /* プロットボタンの背景色 */
  color: white; /* プロットボタンの文字色 */
  padding: 10px 24px; /* プロットボタンのパディング */
  border: none; /* プロットボタンの境界線をなしにする */
  border-radius: 4px; /* プロットボタンの角を丸くする */
  cursor: pointer; /* プロットボタンのカーソルをポインターにする */
}

/* プロットコンテナのスタイル */
.plot-container {
  width: 100%; /* プロットコンテナの幅を100%にする */
  height: 500px; /* プロットコンテナの高さを500pxにする */
  /* border: 1px solid #ccc; プロットコンテナの境界線 */
  margin-top: 20px; /* プロットコンテナの上部マージン */
}

/* ヘッダーエリアのスタイル */
.header {
  display: flex; /* ヘッダーエリアのディスプレイをフレックスにする */
  align-items: center; /* ヘッダーエリアのアイテムを中央揃え */
  justify-content: flex-start; /* ヘッダーエリアのアイテムを左揃え */
  margin-bottom: 20px; /* ヘッダーエリアの下部マージン */
}

/* ヘッダー左部分のスタイル */
.header-left {
  display: flex; /* ヘッダー左部分のディスプレイをフレックスにする */
  align-items: center; /* ヘッダー左部分のアイテムを中央揃え */
  gap: 10px; /* ヘッダー左部分のアイテム間のギャップ */
}

/* コントロールエリアのスタイル */
.controls {
  display: flex; /* コントロールエリアのディスプレイをフレックスにする */
  gap: 10px; /* コントロールエリアのアイテム間のギャップ */
}

/* ボタンのスタイル */
button {
  background-color: grey; /* ボタンの背景色 */
  border: black; /* ボタンの境界線 */
  color: black; /* ボタンの文字色 */
  padding: 5px 20px; /* ボタンのパディング */
  text-align: center; /* ボタンのテキストを中央揃え */
  text-decoration: none; /* ボタンのテキスト装飾をなしにする */
  font-size: 15px; /* ボタンのフォントサイズ */
  margin: 4px 2px; /* ボタンのマージン */
  cursor: pointer; /* ボタンのカーソルをポインターにする */
  border-radius: 4px; /* ボタンの角を丸くする */
}

/* ファイル入力のスタイル */
input[type="file"] {
  margin-right: 10px; /* ファイル入力の右マージン */
}

/* テーブル情報のスタイル */
.table-info {
  font-size: 14px; /* テーブル情報のフォントサイズ */
  text-align: left; /* テーブル情報のテキストを左揃え */
}

/* テーブルコンテナのスタイル */
.table-container {
  max-height: 400px; /* テーブルコンテナの最大高さ */
  overflow-y: auto; /* テーブルコンテナの縦方向のオーバーフローを自動にする */
}

table {
  width: 100%; /* テーブルの幅 */
  border-collapse: collapse; /* テーブルの境界線を結合 */
  background-color: #ffffff; /* テーブルの背景色 */
}

th, td {
  border: 1px solid #ddd; /* テーブルヘッダーとデータセルの境界線 */
  padding: 8px; /* テーブルヘッダーとデータセルのパディング */
  text-align: left; /* テーブルヘッダーとデータセルのテキストを左揃え */
  color: #333; /* テーブルヘッダーとデータセルの文字色 */
  font-size: 12px; /* テーブルヘッダーとデータセルのフォントサイズ */
}

thead {
  position: sticky; /* テーブルヘッダーの位置を固定 */
  top: 0; /* テーブルヘッダーの上部位置 */
  background-color: #f2f2f2; /* テーブルヘッダーの背景色 */
  z-index: 1; /* テーブルヘッダーの重なり順序 */
}

tr:nth-child(even) {
  background-color: #f9f9f9; /* 偶数行の背景色 */
}

.header-cell {
  white-space: pre-wrap; /* ヘッダーセルの空白を保持 */
  word-wrap: break-word; /* ヘッダーセルの単語を折り返し */
}

/* プロット設定のスタイル */
.plot-settings {
  margin-bottom: 20px; /* プロット設定の下部マージン */
  display: flex; /* プロット設定のディスプレイをフレックスにする */
  flex-wrap: wrap; /* プロット設定のアイテムを折り返し */
  gap: 10px; /* プロット設定のアイテム間のギャップ */
  padding: 10px; /* プロット設定のパディング */
  border: 1px solid #ddd; /* プロット設定の境界線 */
}
.plot-settings label {
  display: flex; /* プロット設定のラベルのディスプレイをフレックスにする */
  flex-direction: column; /* プロット設定のラベルの方向を縦にする */
}
.plot-settings select {
  margin-top: 5px; /* プロット設定のセレクトの上部マージン */
  padding: 5px; /* プロット設定のセレクトのパディング */
  font-size: 14px; /* プロット設定のセレクトのフォントサイズ */
  border: 1px solid #ddd; /* プロット設定のセレクトの境界線 */
  background-color: white; /* プロット設定のセレクトの背景色 */
  color: #4d4d4d; /* プロット設定のセレクトの文字色 */
}

.plot-controls {
  display: flex; /* プロットコントロールのディスプレイをフレックスにする */
  flex-direction: column; /* プロットコントロールの方向を縦にする */
  gap: 10px; /* プロットコントロールのアイテム間のギャップ */
  margin-bottom: 20px; /* プロットコントロールの下部マージン */
}

.plot-settings-row {
  display: flex; /* プロット設定行のディスプレイをフレックスにする */
  flex-wrap: wrap; /* プロット設定行のアイテムを折り返し */
  gap: 10px; /* プロット設定行のアイテム間のギャップ */
  align-items: center; /* プロット設定行のアイテムを中央揃え */
}

.plot-settings-row label {
  display: flex; /* プロット設定行のラベルのディスプレイをフレックスにする */
  flex-direction: column; /* プロット設定行のラベルの方向を縦にする */
  align-items: flex-start; /* プロット設定行のラベルのアイテムを左揃え */
}

.plot-settings-row input[type="range"] {
  margin-top: 5px; /* プロット設定行のレンジ入力の上部マージン */
}

.reset-button {
  margin-left: auto; /* リセットボタンの左マージンを自動にする */
}

.plot-button {
  background-color: #007bff; /* プロットボタンの背景色 */
  color: white; /* プロットボタンの文字色 */
  font-size: 16px; /* プロットボタンのフォントサイズ */
  padding: 10px 20px; /* プロットボタンのパディング */
  margin: 0 auto; /* プロットボタンのマージン */
  display: block; /* プロットボタンのディスプレイをブロックにする */
}

.split-view {
  display: flex; /* スプリットビューのディスプレイをフレックスにする */
  height: calc(100vh - 100px); /* スプリットビューの高さを計算 */
}

.resizable-divider {
  width: 5px; /* リサイズ可能なディバイダーの幅 */
  cursor: ew-resize; /* リサイズ可能なディバイダーのカーソル */
  background-color: #ccc; /* リサイズ可能なディバイダーの背景色 */
  position: relative; /* リサイズ可能なディバイダーの位置 */
}

.resizable-divider:after {
  content: ''; /* リサイズ可能なディバイダーの後のコンテンツ */
  display: block; /* リサイズ可能なディバイダーの後のディスプレイ */
  height: 100%; /* リサイズ可能なディバイダーの後の高さ */
  width: 100%; /* リサイズ可能なディバイダーの後の幅 */
  position: absolute; /* リサイズ可能なディバイダーの後の位置 */
  left: 0; /* リサイズ可能なディバイダーの後の左位置 */
  top: 0; /* リサイズ可能なディバイダーの後の上位置 */
}

.left-view, .right-view {
  overflow: auto; /* 左ビューと右ビューのオーバーフローを自動にする */
  padding: 10px; /* 左ビューと右ビューのパディング */
  box-sizing: border-box; /* 左ビューと右ビューのボックスサイズをボーダーボックスにする */
}

.left-view {
  flex: 4; /* 左ビューのフレックス */
  border-right: 1px solid #ddd; /* 左ビューの右境界線 */
}

.right-view {
  flex: 6; /* 右ビューのフレックス */
  display: flex; /* 右ビューのディスプレイをフレックスにする */
  flex-direction: column; /* 右ビューの方向を縦にする */
}

.plot-container {
  flex: 1; /* プロットコンテナのフレックス */
  margin-top: 20px; /* プロットコンテナの上部マージン */
}

.sticky-column {
  position: sticky; /* スティッキーカラムの位置を固定 */
  left: 0; /* スティッキーカラムの左位置 */
  /* background-color: #f2f2f2; スティッキーカラムの背景色 */
  z-index: 2; /* スティッキーカラムの重なり順序 */
}

/* 前処理コントロールのスタイル */
.preprocessing-controls {
  margin-bottom: 20px; /* 前処理コントロールの下部マージン */
}

.preprocessing-controls h3 {
  margin-bottom: 10px; /* 前処理コントロールの見出しの下部マージン */
}

.preprocessing-controls div {
  margin-bottom: 10px; /* 前処理コントロールのディブの下部マージン */
}

.filter-by-value {
  display: flex; /* 値でフィルターのディスプレイをフレックスにする */
  gap: 10px; /* 値でフィルターのアイテム間のギャップ */
  align-items: center; /* 値でフィルターのアイテムを中央揃え */
  width: 100%; /* 値でフィルターの幅 */
  max-width: 600px; /* 値でフィルターの最大幅 */
  height: 150px; /* 値でフィルターの高さ */
  border-top: 1px solid #ddd; /* 値でフィルターの上境界線 */
  border-bottom: 1px solid #ddd; /* 値でフィルターの下境界線 */
  padding: 10px; /* 値でフィルターのパディング */
}

.filter-left {
  flex: 1; /* フィルター左のフレックス */
}

.filter-right {
  flex: 1; /* フィルター右のフレックス */
  overflow-y: auto; /* フィルター右の縦方向のオーバーフローを自動にする */
  height: 100%; /* フィルター右の高さ */
}

.multiselect-container {
  display: flex; /* マルチセレクトコンテナのディスプレイをフレックスにする */
  flex-wrap: wrap; /* マルチセレクトコンテナのアイテムを折り返し */
  gap: 5px; /* マルチセレクトコンテナのアイテム間のギャップ */
}

.multiselect-container div {
  padding: 5px; /* マルチセレクトコンテナのディブのパディング */
  border: 1px solid #ddd; /* マルチセレクトコンテナのディブの境界線 */
  background-color: white; /* マルチセレクトコンテナのディブの背景色 */
  cursor: pointer; /* マルチセレクトコンテナのディブのカーソル */
  width: 100px; /* マルチセレクトコンテナのディブの幅を固定 */
  white-space: nowrap; /* マルチセレクトコンテナのディブの空白を折り返さない */
  overflow: hidden; /* マルチセレクトコンテナのディブのオーバーフローを隠す */
  text-overflow: ellipsis; /* マルチセレクトコンテナのディブのテキストを省略記号で切る */
}

.multiselect-container div.selected {
  background-color: lightblue; /* マルチセレクトコンテナの選択されたディブの背景色 */
}
</style>
