const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '../data');
const HISTORY_FILE = path.join(DATA_DIR, 'history.json');
const STATUS_FILE = path.join(DATA_DIR, 'status.json');

function loadJson(filePath, defaultValue) {
  if (fs.existsSync(filePath)) {
    try {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (e) {
      return defaultValue;
    }
  }
  return defaultValue;
}

function saveJson(filePath, data) {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
}

/**
 * 외부에서 입력된 데이터(정상/장애)를 T04 규격에 맞게 정규화 및 저장 처리하는 파이프라인
 */
function processReading(readingInput) {
  const history = loadJson(HISTORY_FILE, {});
  const currentStatus = loadJson(STATUS_FILE, { status: 'fresh', error_code: 'none', last_observed_at: null });

  // 1. 에러/장애 발생 시: 기존 history 데이터 보존 + stale 상태 변경
  if (readingInput.error_code && readingInput.error_code !== 'none') {
    currentStatus.status = 'stale';
    currentStatus.error_code = readingInput.error_code;
    saveJson(STATUS_FILE, currentStatus);
    return { success: false, status: currentStatus };
  }

  // 2. 정상 응답 시: record_date 기준 원자적 덮어쓰기(Upsert)
  const recordDate = readingInput.observed_at ? readingInput.observed_at.split('T')[0] : (readingInput.record_date || new Date().toISOString().split('T')[0]);
  const normalizedReading = {
    signal_id: readingInput.signal_id || 'T04-CABBAGE',
    source_url: readingInput.source_url || 'https://apis.data.go.kr',
    source_observed_at: readingInput.observed_at || new Date().toISOString(),
    normalized_value: readingInput.value !== undefined ? readingInput.value : readingInput.normalized_value,
    unit: readingInput.unit || '원',
    record_date: recordDate
  };

  history[recordDate] = normalizedReading;
  saveJson(HISTORY_FILE, history);

  // 3. 상태 정상(fresh/none) 복구
  currentStatus.status = 'fresh';
  currentStatus.error_code = 'none';
  currentStatus.last_observed_at = normalizedReading.source_observed_at;
  saveJson(STATUS_FILE, currentStatus);

  return { success: true, reading: normalizedReading, status: currentStatus };
}

function resetPipeline() {
  saveJson(HISTORY_FILE, {});
  saveJson(STATUS_FILE, { status: 'fresh', error_code: 'none', last_observed_at: null });
}

module.exports = { processReading, resetPipeline };
