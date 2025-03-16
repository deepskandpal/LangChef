import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import {
  promptsApi,
  datasetsApi,
  experimentsApi,
  tracesApi,
  metricsApi
} from './api';

// Create a mock for the axios instance
const mock = new MockAdapter(axios);

describe('API Services', () => {
  afterEach(() => {
    mock.reset();
  });

  // Test promptsApi
  describe('promptsApi', () => {
    it('should get all prompts', async () => {
      const mockPrompts = [
        { id: 1, name: 'Prompt 1' },
        { id: 2, name: 'Prompt 2' }
      ];
      
      mock.onGet('/prompts').reply(200, mockPrompts);
      
      const response = await promptsApi.getAll();
      expect(response.data).toEqual(mockPrompts);
    });
    
    it('should get a prompt by ID', async () => {
      const mockPrompt = { id: 1, name: 'Prompt 1' };
      
      mock.onGet('/prompts/1').reply(200, mockPrompt);
      
      const response = await promptsApi.getById(1);
      expect(response.data).toEqual(mockPrompt);
    });
    
    it('should create a prompt', async () => {
      const newPrompt = { name: 'New Prompt', description: 'Test prompt' };
      const createdPrompt = { id: 3, ...newPrompt };
      
      mock.onPost('/prompts').reply(201, createdPrompt);
      
      const response = await promptsApi.create(newPrompt);
      expect(response.data).toEqual(createdPrompt);
    });
  });

  // Test datasetsApi
  describe('datasetsApi', () => {
    it('should get all datasets', async () => {
      const mockDatasets = [
        { id: 1, name: 'Dataset 1', type: 'csv' },
        { id: 2, name: 'Dataset 2', type: 'json' }
      ];
      
      mock.onGet('/datasets').reply(200, mockDatasets);
      
      const response = await datasetsApi.getAll();
      expect(response.data).toEqual(mockDatasets);
    });
    
    it('should create a dataset', async () => {
      const newDataset = { 
        name: 'New Dataset', 
        description: 'Test dataset',
        type: 'csv',
        items: [{ name: 'Item 1', value: 'Value 1' }]
      };
      const createdDataset = { id: 3, ...newDataset };
      
      mock.onPost('/datasets').reply(201, createdDataset);
      
      const response = await datasetsApi.create(newDataset);
      expect(response.data).toEqual(createdDataset);
    });
    
    it('should get dataset items', async () => {
      const mockItems = [
        { id: 1, content: { name: 'Item 1' } },
        { id: 2, content: { name: 'Item 2' } }
      ];
      
      mock.onGet('/datasets/1/items').reply(200, mockItems);
      
      const response = await datasetsApi.getItems(1);
      expect(response.data).toEqual(mockItems);
    });

    it('should upload a CSV file', async () => {
      // Create a mock file and FormData
      const file = new File(['test,content'], 'test.csv', { type: 'text/csv' });
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', 'Test CSV');
      formData.append('description', 'Test description');
      formData.append('file_type', 'csv');
      
      const mockResponse = { 
        id: 1, 
        name: 'Test CSV', 
        description: 'Test description',
        type: 'csv' 
      };
      
      // Mock the file.text() method for testing the uploadCSV method
      file.text = jest.fn().mockResolvedValue('header1,header2\nvalue1,value2');
      
      // Mock both endpoints that could be used by uploadCSV
      mock.onPost('/datasets/upload/file').reply(200, mockResponse);
      mock.onPost('/datasets/').reply(201, mockResponse);
      
      const response = await datasetsApi.uploadCSV(formData);
      expect(response.data).toEqual(mockResponse);
    });
  });

  // Test experimentsApi
  describe('experimentsApi', () => {
    it('should get all experiments', async () => {
      const mockExperiments = [
        { id: 1, name: 'Experiment 1' },
        { id: 2, name: 'Experiment 2' }
      ];
      
      mock.onGet('/experiments').reply(200, mockExperiments);
      
      const response = await experimentsApi.getAll();
      expect(response.data).toEqual(mockExperiments);
    });
    
    it('should get experiment results', async () => {
      const mockResults = [
        { id: 1, score: 0.95 },
        { id: 2, score: 0.87 }
      ];
      
      mock.onGet('/experiments/1/results').reply(200, mockResults);
      
      const response = await experimentsApi.getResults(1);
      expect(response.data).toEqual(mockResults);
    });
  });

  // Test tracesApi
  describe('tracesApi', () => {
    it('should get all traces', async () => {
      const mockTraces = [
        { id: 1, name: 'Trace 1' },
        { id: 2, name: 'Trace 2' }
      ];
      
      mock.onGet('/traces').reply(200, mockTraces);
      
      const response = await tracesApi.getAll();
      expect(response.data).toEqual(mockTraces);
    });
    
    it('should create a trace', async () => {
      const newTrace = { name: 'New Trace', description: 'Test trace' };
      const createdTrace = { id: 3, ...newTrace };
      
      mock.onPost('/traces').reply(201, createdTrace);
      
      const response = await tracesApi.create(newTrace);
      expect(response.data).toEqual(createdTrace);
    });
  });

  // Test metricsApi
  describe('metricsApi', () => {
    it('should get dashboard metrics', async () => {
      const mockMetrics = {
        datasets: 10,
        experiments: 5,
        traces: 20
      };
      
      mock.onGet('/metrics/dashboard').reply(200, mockMetrics);
      
      const response = await metricsApi.getDashboard();
      expect(response.data).toEqual(mockMetrics);
    });
    
    it('should get experiment summary metrics', async () => {
      const mockSummary = {
        id: 1,
        name: 'Experiment 1',
        results: {
          accuracy: 0.95,
          precision: 0.92
        }
      };
      
      mock.onGet('/metrics/experiments/1/summary').reply(200, mockSummary);
      
      const response = await metricsApi.getExperimentSummary(1);
      expect(response.data).toEqual(mockSummary);
    });
  });
}); 