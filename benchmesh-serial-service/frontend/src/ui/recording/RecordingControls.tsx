import React, { useState } from 'react';
import { RecordingApi, StartRecordingRequest, ChannelConfig } from '../../api/recordingApi';
import { Instrument } from '../InstrumentPod';

interface RecordingControlsProps {
  apiBase: string;
  instruments: Instrument[];
  onRecordingStarted: (seriesId: number) => void;
}

export const RecordingControls: React.FC<RecordingControlsProps> = ({
  apiBase,
  instruments,
  onRecordingStarted
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [interval, setInterval] = useState(2.0);
  const [selectedChannels, setSelectedChannels] = useState<ChannelConfig[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const api = new RecordingApi(apiBase);

  const handleAddChannel = () => {
    if (instruments.length > 0) {
      const firstInstrument = instruments[0];
      const firstClass = firstInstrument.classes && firstInstrument.classes.length > 0
        ? firstInstrument.classes[0].class
        : 'PSU';
      setSelectedChannels([
        ...selectedChannels,
        {
          device_id: firstInstrument.id,
          class_name: firstClass,
          channel: 1,
          method_name: 'voltage',
          label: `${firstInstrument.id} voltage`
        }
      ]);
    }
  };

  const handleRemoveChannel = (index: number) => {
    setSelectedChannels(selectedChannels.filter((_, i) => i !== index));
  };

  const handleChannelChange = (index: number, field: keyof ChannelConfig, value: any) => {
    const updated = [...selectedChannels];
    updated[index] = { ...updated[index], [field]: value };
    setSelectedChannels(updated);
  };

  const handleStartRecording = async () => {
    if (!name.trim()) {
      setError('Recording name is required');
      return;
    }

    if (selectedChannels.length === 0) {
      setError('At least one channel must be selected');
      return;
    }

    setIsStarting(true);
    setError(null);

    try {
      const request: StartRecordingRequest = {
        name: name.trim(),
        channels: selectedChannels,
        interval_seconds: interval,
        description: description.trim() || undefined
      };

      const response = await api.startRecording(request);
      console.log('[RecordingControls] Recording started:', response);

      onRecordingStarted(response.series_id);

      // Reset form
      setName('');
      setDescription('');
      setSelectedChannels([]);
    } catch (err: any) {
      console.error('[RecordingControls] Failed to start recording:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to start recording');
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div style={{ padding: '20px', background: 'var(--card)', borderRadius: '8px' }}>
      <h3 style={{ marginTop: 0 }}>Start New Recording</h3>

      {error && (
        <div style={{
          padding: '10px',
          background: '#ff4d4f',
          color: 'white',
          borderRadius: '4px',
          marginBottom: '15px'
        }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
          Recording Name *
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Power Supply Test 1"
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid var(--border)',
            fontSize: '14px'
          }}
        />
      </div>

      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
          Description (optional)
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe this recording..."
          rows={3}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid var(--border)',
            fontSize: '14px',
            resize: 'vertical'
          }}
        />
      </div>

      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
          Sampling Interval (seconds)
        </label>
        <input
          type="number"
          value={interval}
          onChange={(e) => setInterval(parseFloat(e.target.value))}
          min={0.1}
          step={0.1}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid var(--border)',
            fontSize: '14px'
          }}
        />
      </div>

      <div style={{ marginBottom: '15px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <label style={{ fontWeight: 'bold' }}>Channels *</label>
          <button
            onClick={handleAddChannel}
            disabled={instruments.length === 0}
            style={{
              padding: '5px 15px',
              background: '#52c41a',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: instruments.length > 0 ? 'pointer' : 'not-allowed',
              fontSize: '14px'
            }}
          >
            + Add Channel
          </button>
        </div>

        {selectedChannels.length === 0 && (
          <div style={{
            padding: '20px',
            textAlign: 'center',
            color: 'var(--text-2)',
            border: '1px dashed var(--border)',
            borderRadius: '4px'
          }}>
            No channels selected. Click "Add Channel" to start.
          </div>
        )}

        {selectedChannels.map((channel, index) => (
          <div
            key={index}
            style={{
              padding: '10px',
              background: 'var(--bg-1)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              marginBottom: '10px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong>Channel {index + 1}</strong>
              <button
                onClick={() => handleRemoveChannel(index)}
                style={{
                  background: '#ff4d4f',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '2px 8px',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Remove
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', marginBottom: '3px' }}>Device</label>
                <select
                  value={channel.device_id}
                  onChange={(e) => handleChannelChange(index, 'device_id', e.target.value)}
                  style={{ width: '100%', padding: '5px', borderRadius: '4px', border: '1px solid var(--border)' }}
                >
                  {instruments.map((inst) => (
                    <option key={inst.id} value={inst.id}>
                      {inst.id} ({inst.classes.map(c => c.class).join(', ')})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', marginBottom: '3px' }}>Class</label>
                <input
                  type="text"
                  value={channel.class_name}
                  onChange={(e) => handleChannelChange(index, 'class_name', e.target.value)}
                  style={{ width: '100%', padding: '5px', borderRadius: '4px', border: '1px solid var(--border)' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', marginBottom: '3px' }}>Channel #</label>
                <input
                  type="number"
                  value={channel.channel}
                  onChange={(e) => handleChannelChange(index, 'channel', parseInt(e.target.value))}
                  min={1}
                  style={{ width: '100%', padding: '5px', borderRadius: '4px', border: '1px solid var(--border)' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', marginBottom: '3px' }}>Method</label>
                <input
                  type="text"
                  value={channel.method_name}
                  onChange={(e) => handleChannelChange(index, 'method_name', e.target.value)}
                  placeholder="e.g., voltage"
                  style={{ width: '100%', padding: '5px', borderRadius: '4px', border: '1px solid var(--border)' }}
                />
              </div>

              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', fontSize: '12px', marginBottom: '3px' }}>Label (optional)</label>
                <input
                  type="text"
                  value={channel.label || ''}
                  onChange={(e) => handleChannelChange(index, 'label', e.target.value)}
                  placeholder="e.g., PSU Output Voltage"
                  style={{ width: '100%', padding: '5px', borderRadius: '4px', border: '1px solid var(--border)' }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={handleStartRecording}
        disabled={isStarting || !name.trim() || selectedChannels.length === 0}
        style={{
          width: '100%',
          padding: '12px',
          background: isStarting ? '#ccc' : '#1890ff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: isStarting || !name.trim() || selectedChannels.length === 0 ? 'not-allowed' : 'pointer',
          fontSize: '16px',
          fontWeight: 'bold'
        }}
      >
        {isStarting ? 'Starting...' : '🔴 Start Recording'}
      </button>
    </div>
  );
};
