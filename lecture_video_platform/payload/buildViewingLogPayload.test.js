const { buildViewingLogPayload } = require('./buildViewingLogPayload');

describe('buildViewingLogPayload', () => {
  const fixedDate = new Date('2026-02-23T11:18:42.000Z');

  it('returns object with all keys required by POST /api/viewing-log', () => {
    const payload = buildViewingLogPayload('1', 0, 'play', 0, fixedDate);
    expect(payload).toEqual({
      participant_id: '1',
      time_stamp: '2026-02-23T11:18:42.000Z',
      current_time: 0,
      action: 'play',
      duration: 0,
    });
  });

  it('stringifies participant_id', () => {
    const payload = buildViewingLogPayload(1, 0, 'play', 0, fixedDate);
    expect(payload.participant_id).toBe('1');
  });

  it('uses time_stamp from given now (testability)', () => {
    const payload = buildViewingLogPayload('1', 120, 'pause', 0, fixedDate);
    expect(payload.time_stamp).toBe('2026-02-23T11:18:42.000Z');
  });

  it('coerces current_time and duration to number', () => {
    const payload = buildViewingLogPayload('1', '90.5', 'forward_skip', '5', fixedDate);
    expect(payload.current_time).toBe(90.5);
    expect(payload.duration).toBe(5);
  });

  it('handles negative duration (e.g. backward_skip)', () => {
    const payload = buildViewingLogPayload('1', 60, 'backward_skip', -5, fixedDate);
    expect(payload.duration).toBe(-5);
  });

  it('handles seek actions with duration', () => {
    const payload = buildViewingLogPayload('1', 30, 'forward_seek', 10.5, fixedDate);
    expect(payload.action).toBe('forward_seek');
    expect(payload.duration).toBe(10.5);
  });
});
