import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { RecordingApi, RecordingSeries, DataPoint } from '../../api/recordingApi';
import { LiveChart } from './LiveChart';

interface RecordingDetailsProps {
  seriesId: number;
  apiBase: string;
  onClose: () => void;
}

export const RecordingDetails: React.FC<RecordingDetailsProps> = ({ seriesId, apiBase, onClose }) => {
  const [series, setSeries] = useState<RecordingSeries | null>(null);
  const [dataPoints, setDataPoints] = useState<DataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLiveChart, setShowLiveChart] = useState(false);

  const api = new RecordingApi(apiBase);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [detailsResp, dataResp] = await Promise.all([
          api.getRecordingDetails(seriesId),
          api.getRecordingData(seriesId, 0, 10000) // Load up to 10k points
        ]);

        setSeries(detailsResp.series);
        setDataPoints(dataResp.data_points);

        // Enable live chart if recording is active
        if (detailsResp.series.status === 'recording' || detailsResp.series.status === 'paused') {
          setShowLiveChart(true);
        }
      } catch (err: any) {
        console.error('[RecordingDetails] Failed to load data:', err);
        setError(err.message || 'Failed to load recording details');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [seriesId, apiBase]);

  const handleExport = async () => {
    try {
      const blob = await api.exportToCsv(seriesId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${series?.name.replace(/\s+/g, '_')}_${seriesId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error('[RecordingDetails] Failed to export:', err);
      alert(`Failed to export: ${err.message}`);
    }
  };

  const chartOptions = React.useMemo(() => {
    if (!series || dataPoints.length === 0) {
      return {
        title: {
          text: 'No data available',
          left: 'center',
          top: 'center',
          textStyle: {
            fontSize: 16,
            color: 'var(--text-2)'
          }
        }
      } as any;
    }

    // Extract time series for each channel
    const timeData = dataPoints.map(dp => {
      const seconds = typeof dp.elapsed_seconds === 'number' ? dp.elapsed_seconds : parseFloat(dp.elapsed_seconds);
      return isNaN(seconds) ? 0 : seconds;
    });
    const chartSeries: any[] = [];

    series.channels.forEach((channel, idx) => {
      const channelKey = `${channel.device_id}_${channel.class_name}_${channel.channel}_${channel.method_name}`;
      const valueData = dataPoints.map(dp => {
        const value = dp.measurements[channelKey];
        if (value === undefined || value === null) return null;
        // Convert string values to numbers
        const numValue = typeof value === 'number' ? value : parseFloat(value);
        return isNaN(numValue) ? null : numValue;
      });

      const label = channel.label || `${channel.device_id} ${channel.method_name}`;

      chartSeries.push({
        name: label,
        type: 'line',
        smooth: true,
        symbol: 'none',
        sampling: 'lttb',
        lineStyle: {
          width: 2
        },
        emphasis: {
          focus: 'series'
        },
        data: valueData
      });
    });

    return {
      title: {
        text: series.name,
        subtext: series.description || '',
        left: 'center',
        textStyle: {
          fontSize: 20,
          fontWeight: 700
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          const time = params[0].axisValue;
          const timeNum = typeof time === 'number' ? time : parseFloat(time);
          const timeStr = !isNaN(timeNum) ? timeNum.toFixed(2) : time;
          let tooltip = `<b>Time: ${timeStr}s</b><br/>`;
          params.forEach((param: any) => {
            if (param.value !== null && param.value !== undefined) {
              const val = typeof param.value === 'number' ? param.value : parseFloat(param.value);
              const valStr = !isNaN(val) ? val.toFixed(3) : param.value;
              tooltip += `${param.marker} ${param.seriesName}: ${valStr}<br/>`;
            }
          });
          return tooltip;
        }
      },
      legend: {
        data: chartSeries.map(s => s.name),
        top: 60,
        type: 'scroll'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
        top: 110
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: timeData,
        name: 'Time (s)',
        nameLocation: 'middle',
        nameGap: 30,
        axisLabel: {
          formatter: (value: any) => {
            const num = typeof value === 'number' ? value : parseFloat(value);
            return !isNaN(num) ? num.toFixed(1) : String(value);
          }
        }
      },
      yAxis: {
        type: 'value',
        name: 'Value',
        nameLocation: 'middle',
        nameGap: 50
      },
      series: chartSeries,
      animation: false,
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          start: 0,
          end: 100,
          handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
          handleSize: '80%',
          handleStyle: {
            color: '#fff',
            shadowBlur: 3,
            shadowColor: 'rgba(0, 0, 0, 0.6)',
            shadowOffsetX: 2,
            shadowOffsetY: 2
          }
        }
      ],
      toolbox: {
        feature: {
          saveAsImage: {
            title: 'Save as Image',
            name: `recording_${seriesId}_historical`
          },
          dataZoom: {
            yAxisIndex: 'none',
            title: {
              zoom: 'Zoom',
              back: 'Reset Zoom'
            }
          },
          restore: {
            title: 'Restore'
          }
        },
        right: 20
      }
    };
  }, [series, dataPoints, seriesId]);

  if (loading) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}>
        <div style={{ background: 'var(--bg-1)', padding: '40px', borderRadius: '8px' }}>
          Loading recording details...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}>
        <div style={{ background: 'var(--bg-1)', padding: '40px', borderRadius: '8px' }}>
          <h3 style={{ color: '#ff4d4f' }}>Error</h3>
          <p>{error}</p>
          <button onClick={onClose} style={{ padding: '8px 16px', cursor: 'pointer' }}>
            Close
          </button>
        </div>
      </div>
    );
  }

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}h ${minutes}m ${secs}s`;
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--bg-1)',
        borderRadius: '8px',
        maxWidth: '1200px',
        width: '100%',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px',
          borderBottom: '1px solid #d9d9d9',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h2 style={{ margin: 0 }}>{series?.name}</h2>
            <p style={{ margin: '5px 0 0', color: 'var(--text-1)', fontSize: '14px' }}>{series?.description}</p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              padding: '0',
              width: '32px',
              height: '32px'
            }}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          {/* Info */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '15px',
            marginBottom: '20px',
            padding: '15px',
            background: 'var(--card)',
            borderRadius: '8px'
          }}>
            <div>
              <strong>Status:</strong> {series?.status}
            </div>
            <div>
              <strong>Duration:</strong> {formatDuration(series?.total_duration_seconds)}
            </div>
            <div>
              <strong>Data Points:</strong> {dataPoints.length}
            </div>
            <div>
              <strong>Interval:</strong> {series?.interval_seconds}s
            </div>
            <div>
              <strong>Started:</strong> {series ? new Date(series.start_time).toLocaleString() : 'N/A'}
            </div>
            {series?.end_time && (
              <div>
                <strong>Ended:</strong> {new Date(series.end_time).toLocaleString()}
              </div>
            )}
          </div>

          {/* Channels */}
          <div style={{ marginBottom: '20px' }}>
            <h4>Channels:</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {series?.channels.map((ch, idx) => (
                <div key={idx} style={{
                  padding: '8px 12px',
                  background: '#e6f7ff',
                  border: '1px solid #91d5ff',
                  borderRadius: '4px',
                  fontSize: '13px'
                }}>
                  {ch.label || `${ch.device_id} ${ch.method_name}`}
                </div>
              ))}
            </div>
          </div>

          {/* Charts */}
          {showLiveChart && (
            <div style={{ marginBottom: '20px' }}>
              <h4>Live Data:</h4>
              <div style={{ height: '400px', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px' }}>
                <LiveChart
                  seriesId={seriesId}
                  channels={series?.channels || []}
                  apiBase={apiBase}
                  isActive={true}
                />
              </div>
            </div>
          )}

          <div>
            <h4>Historical Data:</h4>
            <div style={{ height: '400px', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px' }}>
              <ReactECharts
                option={chartOptions}
                style={{ height: '100%', width: '100%' }}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '20px',
          borderTop: '1px solid #d9d9d9',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '10px'
        }}>
          <button
            onClick={handleExport}
            style={{
              padding: '10px 20px',
              background: '#722ed1',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            💾 Export CSV
          </button>
          <button
            onClick={onClose}
            style={{
              padding: '10px 20px',
              background: 'var(--card-hover)',
              color: 'var(--text-0)',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
