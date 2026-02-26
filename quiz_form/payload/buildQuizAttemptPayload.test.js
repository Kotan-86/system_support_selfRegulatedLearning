const { buildQuizAttemptPayload } = require('./buildQuizAttemptPayload');

describe('buildQuizAttemptPayload', () => {
  const answers = [
    { question_index: 1, selected_answer: 'A', is_correct: 1 },
    { question_index: 2, selected_answer: 'B', is_correct: 0 },
  ];

  it('returns object with all keys required by POST /api/quiz-attempts', () => {
    const payload = buildQuizAttemptPayload('1', '2026-01-20T11:30:38', 4, 5, answers);
    expect(payload).toEqual({
      participant_id: '1',
      timestamp: '2026-01-20T11:30:38',
      score_numerator: 4,
      score_denominator: 5,
      answers: [
        { question_index: 1, selected_answer: 'A', is_correct: 1 },
        { question_index: 2, selected_answer: 'B', is_correct: 0 },
      ],
    });
  });

  it('stringifies participant_id', () => {
    const payload = buildQuizAttemptPayload(1, '2026-01-20T11:30:38', 4, 5, answers);
    expect(payload.participant_id).toBe('1');
  });

  it('normalizes is_correct to 0 or 1', () => {
    const payload = buildQuizAttemptPayload('1', '2026-01-20T11:30:38', 1, 2, [
      { question_index: 1, selected_answer: 'X', is_correct: true },
      { question_index: 2, selected_answer: 'Y', is_correct: false },
    ]);
    expect(payload.answers[0].is_correct).toBe(1);
    expect(payload.answers[1].is_correct).toBe(0);
  });

  it('coerces score_numerator and score_denominator to number', () => {
    const payload = buildQuizAttemptPayload('1', '2026-01-20T11:30:38', '4', '5', answers);
    expect(payload.score_numerator).toBe(4);
    expect(payload.score_denominator).toBe(5);
  });
});
