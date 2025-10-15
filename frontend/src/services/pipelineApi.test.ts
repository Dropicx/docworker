/**
 * Tests for Pipeline API Service
 */
import { describe, it, expect, beforeEach } from 'vitest';
import PipelineApiService from './pipelineApi';

describe('PipelineApiService', () => {
  let service: PipelineApiService;

  beforeEach(() => {
    service = new PipelineApiService();
  });

  describe('initialization', () => {
    it('should initialize with no token', () => {
      expect(service.isAuthenticated()).toBe(false);
    });
  });

  describe('updateToken', () => {
    it('should update token', () => {
      service.updateToken('test-token');
      expect(service.isAuthenticated()).toBe(true);
    });

    it('should clear token when set to null', () => {
      service.updateToken('test-token');
      expect(service.isAuthenticated()).toBe(true);

      service.updateToken(null);
      expect(service.isAuthenticated()).toBe(false);
    });
  });

  describe('isAuthenticated', () => {
    it('should return false when no token is set', () => {
      expect(service.isAuthenticated()).toBe(false);
    });

    it('should return true when token is set', () => {
      service.updateToken('test-token');
      expect(service.isAuthenticated()).toBe(true);
    });
  });
});
