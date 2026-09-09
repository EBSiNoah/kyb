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
 * Fixture JSON의 중첩된 구조(payload, data 등)와 다양한 필드 구성을 정밀 탐색하는 함수
 */
function extractFixtureData(rawInput) {
  if (!rawInput || typeof rawInput !== 'object') {
    return { isError: true, errorCode: 'schema_break' };
  }

  // 1. 에러 코드 감지 (error_code, error, code 등)
  const errorCode = rawInput.error_code || rawInput.error || rawInput.code || (rawInput.status === 'error' ? 'schema_break' : null);
  if (errorCode && errorCode !== 'none' && errorCode !== 'success' && errorCode !== 200) {
    return { isError: true, errorCode: String(errorCode).toLowerCase() };
  }

  // 2. 중첩된 payload / data 탐색
  const target = rawInput.payload || rawInput.data || rawInput.result || rawInput;

  // 3. 수치값 탐색
  const rawValue = target.normalized_value ?? target.value ?? target.price ?? target.avg_price ?? target.scsbd_prc;

  if (rawValue === undefined || rawValue === null || isNaN(Number(rawValue))) {
    return { isError: true, errorCode: 'schema_break' };
  }

  const normalizedValue = Number(rawValue);

  // 4. 관측 시각 및 날짜 탐색
  const observedAt = target.observed_at || target.source_observed_at || target.timestamp || rawInput.observed_at || new Date().toISOString();
  const recordDate = target.record_date || (observedAt.includes('T') ? observedAt.split('T')[0] : observedAt.substring(0, 10));

  return {
    isError: false,
    data: {
      signal_id: target.signal_id || rawInput.signal_id || 'T04-FIXTURE',
      source_url: target.source_url || rawInput.source_url || 'fixture://external-input',
      source_observed_at: observedAt,
      normalized_value: normalizedValue,
      unit: target.unit || rawInput.unit || '원',
      record_date: recordDate
    }
  };
}

function processReading(readingInput) {
  const history = loadJson(HISTORY_FILE, {});
  const currentStatus = loadJson(STATUS_FILE, { status: 'fresh', error_code: 'none', last_observed_at: null });

  const extracted = extractFixtureData(readingInput);

  // 1. 에러 발생 시: 기존 history 보존 + status stale 변경
  if (extracted.isError) {
    currentStatus.status = 'stale';
    currentStatus.error_code = extracted.errorCode;
    saveJson(STATUS_FILE, currentStatus);
    return { success: false, status: currentStatus };
  }

  // 2. 정상 데이터 수신 시: record_date 키 기준 덮어쓰기 (Upsert)
  const item = extracted.data;
  history[item.record_date] = item;
  saveJson(HISTORY_FILE, history);

  // 3. status fresh 복구
  currentStatus.status = 'fresh';
  currentStatus.error_code = 'none';
  currentStatus.last_observed_at = item.source_observed_at;
  saveJson(STATUS_FILE, currentStatus);

  return { success: true, reading: item, status: currentStatus };
}

function resetPipeline() {
  saveJson(HISTORY_FILE, {});
  saveJson(STATUS_FILE, { status: 'fresh', error_code: 'none', last_observed_at: null });
}

module.exports = { processReading, resetPipeline };
