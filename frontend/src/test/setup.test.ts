/**
 * Basic setup test to ensure test infrastructure is working
 */
import { describe, it, expect } from 'vitest';

describe('Test Setup', () => {
  it('should run tests successfully', () => {
    expect(true).toBe(true);
  });

  it('should have access to test matchers', () => {
    const value = 42;
    expect(value).toBeDefined();
    expect(value).toBe(42);
    expect(typeof value).toBe('number');
  });

  it('should handle basic assertions', () => {
    const array = [1, 2, 3];
    expect(array).toHaveLength(3);
    expect(array).toContain(2);
  });
});
