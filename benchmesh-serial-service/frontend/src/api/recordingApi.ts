import axios from 'axios';

export interface ChannelConfig {
  device_id: string;
  class_name: string;
  channel: number;
  method_name: string;
  label?: string;
}

export interface StartRecordingRequest {
  name: string;
  channels: ChannelConfig[];
  interval_seconds: number;
  description?: string;
}

export interface RecordingSeries {
  id: number;
  name: string;
  description?: string;
  start_time: string;
  end_time?: string;
  status: 'recording' | 'paused' | 'stopped';
  interval_seconds: number;
  channels: ChannelConfig[];
  total_duration_seconds?: number;
  pause_duration_seconds?: number;
  paused_at?: string;
}

export interface DataPoint {
  id: number;
  series_id: number;
  timestamp: string;
  elapsed_seconds: number;
  measurements: Record<string, any>;
}

export interface RecordingListResponse {
  recordings: RecordingSeries[];
}

export interface RecordingDetailsResponse {
  series: RecordingSeries;
  total_points: number;
}

export interface RecordingDataResponse {
  data_points: DataPoint[];
  total_points: number;
  offset: number;
  limit: number;
}

export class RecordingApi {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async startRecording(request: StartRecordingRequest): Promise<{ series_id: number; name: string; status: string }> {
    const response = await axios.post(`${this.baseUrl}/recordings/start`, request);
    return response.data;
  }

  async pauseRecording(seriesId: number): Promise<{ series_id: number; status: string }> {
    const response = await axios.post(`${this.baseUrl}/recordings/${seriesId}/pause`);
    return response.data;
  }

  async resumeRecording(seriesId: number): Promise<{ series_id: number; status: string }> {
    const response = await axios.post(`${this.baseUrl}/recordings/${seriesId}/resume`);
    return response.data;
  }

  async stopRecording(seriesId: number): Promise<{ series_id: number; status: string }> {
    const response = await axios.post(`${this.baseUrl}/recordings/${seriesId}/stop`);
    return response.data;
  }

  async listRecordings(): Promise<RecordingListResponse> {
    const response = await axios.get(`${this.baseUrl}/recordings`);
    return response.data;
  }

  async getRecordingDetails(seriesId: number): Promise<RecordingDetailsResponse> {
    const response = await axios.get(`${this.baseUrl}/recordings/${seriesId}`);
    return response.data;
  }

  async deleteRecording(seriesId: number): Promise<{ message: string }> {
    const response = await axios.delete(`${this.baseUrl}/recordings/${seriesId}`);
    return response.data;
  }

  async getRecordingData(seriesId: number, offset = 0, limit = 1000): Promise<RecordingDataResponse> {
    const response = await axios.get(`${this.baseUrl}/recordings/${seriesId}/data`, {
      params: { offset, limit }
    });
    return response.data;
  }

  async exportToCsv(seriesId: number): Promise<Blob> {
    const response = await axios.get(`${this.baseUrl}/recordings/${seriesId}/export`, {
      responseType: 'blob'
    });
    return response.data;
  }

  createWebSocket(seriesId: number): WebSocket {
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProto}://${window.location.hostname}:57666/recordings/ws/${seriesId}`;
    return new WebSocket(wsUrl);
  }
}
