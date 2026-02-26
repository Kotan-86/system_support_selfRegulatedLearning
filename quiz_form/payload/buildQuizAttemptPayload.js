/**
 * POST /api/quiz-attempts に送る payload を組み立てる純粋関数。
 * GAS の quizForm.gs（onFormSubmit）が送る形と同一仕様。Node でユニットテスト可能。
 *
 * @param {string|number} participant_id - 参加者 ID
 * @param {string} created_at - 受験日時（例: ISO または "yyyy-MM-dd'T'HH:mm:ss"）
 * @param {number} score_numerator - 得点
 * @param {number} score_denominator - 満点
 * @param {Array<{question_index: number, selected_answer: string, is_correct: number}>} answers - 各問の回答
 * @returns {object} API 用 payload
 */
function buildQuizAttemptPayload(participant_id, created_at, score_numerator, score_denominator, answers) {
  return {
    participant_id: String(participant_id),
    timestamp: String(created_at),
    score_numerator: Number(score_numerator),
    score_denominator: Number(score_denominator),
    answers: answers.map((a) => ({
      question_index: Number(a.question_index),
      selected_answer: String(a.selected_answer),
      is_correct: a.is_correct ? 1 : 0,
    })),
  };
}

module.exports = { buildQuizAttemptPayload };
