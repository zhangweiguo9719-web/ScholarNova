/**
 * API 客户端测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { searchApi, papersApi, modelApi, healthApi } from '../client'

// Mock axios
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    post: vi.fn(),
    get: vi.fn(),
  }
  return { default: mockAxios }
})

describe('API Client', () => {
  describe('searchApi', () => {
    it('should call POST /search with request body', async () => {
      const mockResponse = {
        data: {
          run_id: 'test-run-id',
          status: 'pending',
          message: 'Search started',
        },
      }
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.post.mockResolvedValue(mockResponse)

      const result = await searchApi.create({
        query: 'attention mechanism',
        max_results: 10,
      })

      expect(mockedAxios.post).toHaveBeenCalledWith('/search', {
        query: 'attention mechanism',
        max_results: 10,
      })
    })

    it('should call GET /search/{runId}', async () => {
      const mockResponse = {
        data: {
          run_id: 'test-run-id',
          status: 'completed',
          results: [],
        },
      }
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.get.mockResolvedValue(mockResponse)

      await searchApi.getRun('test-run-id')

      expect(mockedAxios.get).toHaveBeenCalledWith('/search/test-run-id')
    })
  })

  describe('papersApi', () => {
    it('should call GET /papers/{paperId}', async () => {
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.get.mockResolvedValue({ data: {} })

      await papersApi.get('paper-123')

      expect(mockedAxios.get).toHaveBeenCalledWith('/papers/paper-123')
    })

    it('should call POST /papers/{paperId}/analyze', async () => {
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.post.mockResolvedValue({ data: {} })

      await papersApi.analyze('paper-123', {
        query: 'summarize',
        analysis_type: 'full',
      })

      expect(mockedAxios.post).toHaveBeenCalledWith('/papers/paper-123/analyze', {
        query: 'summarize',
        analysis_type: 'full',
      })
    })

    it('should call POST /papers/compare', async () => {
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.post.mockResolvedValue({ data: {} })

      await papersApi.compare({
        paper_ids: ['p1', 'p2'],
        query: 'compare methods',
      })

      expect(mockedAxios.post).toHaveBeenCalledWith('/papers/compare', {
        paper_ids: ['p1', 'p2'],
        query: 'compare methods',
      })
    })
  })

  describe('modelApi', () => {
    it('should call POST /model/config', async () => {
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.post.mockResolvedValue({ data: { success: true } })

      await modelApi.saveConfig({
        provider: 'openai',
        model_name: 'gpt-4o',
      })

      expect(mockedAxios.post).toHaveBeenCalledWith('/model/config', {
        provider: 'openai',
        model_name: 'gpt-4o',
      })
    })

    it('should call POST /model/test', async () => {
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.post.mockResolvedValue({
        data: { success: true, latency_ms: 100 },
      })

      await modelApi.testConnection({
        provider: 'openai',
        model_name: 'gpt-4o',
      })

      expect(mockedAxios.post).toHaveBeenCalledWith('/model/test', {
        provider: 'openai',
        model_name: 'gpt-4o',
      })
    })
  })

  describe('healthApi', () => {
    it('should call GET /health', async () => {
      const mockedAxios = vi.mocked(axios.create())
      mockedAxios.get.mockResolvedValue({
        data: { status: 'healthy', version: '1.0.0' },
      })

      await healthApi.check()

      expect(mockedAxios.get).toHaveBeenCalledWith('/health')
    })
  })
})
