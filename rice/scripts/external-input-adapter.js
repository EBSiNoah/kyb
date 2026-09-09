const fs = require('fs');
const { processReading, resetPipeline } = require('./pipeline');

/**
 * 외부 파일 경로, Raw JSON 문자열, 객체 등을 통합 수신하는 어댑터
 */
function handleExternalInput(inputData) {
  let parsedData;

  try {
    if (typeof inputData === 'object' && inputData !== null) {
      parsedData = inputData;
    } else if (typeof inputData === 'string') {
      const trimmed = inputData.trim();
      if (trimmed === 'reset') {
        resetPipeline();
        return { status: { status: 'fresh', error_code: 'none' } };
      }

      if (fs.existsSync(trimmed)) {
        parsedData = JSON.parse(fs.readFileSync(trimmed, 'utf8'));
      } else {
        parsedData = JSON.parse(trimmed);
      }
    } else {
      throw new Error("Invalid Input Format");
    }

    return processReading(parsedData);
  } catch (error) {
    return processReading({ error_code: 'schema_break' });
  }
}

// CLI 및 STDIN 수신 지원
if (require.main === module) {
  const arg = process.argv[2];

  if (arg) {
    const result = handleExternalInput(arg);
    console.log('[External Input Processed]:', result.status);
  } else {
    let stdinData = '';
    process.stdin.on('data', chunk => { stdinData += chunk; });
    process.stdin.on('end', () => {
      const result = handleExternalInput(stdinData);
      console.log('[STDIN Processed]:', result.status);
    });
  }
}

module.exports = { handleExternalInput };
