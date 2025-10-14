import React, { useEffect, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { RecordingApi, ChannelConfig } from '../../api/recordingApi';

interface DataPoint {
  timestamp: string;
  elapsed_seconds: number;
  measurements: Record<string, any>;
}

interface LiveChartProps {
  seriesId: number;
  channels: ChannelConfig[];
  apiBase: string;
  isActive: boolean;
}

export const LiveChart: React.FC<LiveChartProps> = ({ seriesId, channels, apiBase, isActive }) => {
  const [dataPoints, setDataPoints] = useState<DataPoint[]>([]);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const apiRef = useRef(new RecordingApi(apiBase));
  const maxPoints = 1000; // Keep last 1000 points for performance

  useEffect(() => {
    if (!isActive || !seriesId) return;

    const api = apiRef.current;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      try {
        const ws = api.createWebSocket(seriesId);
        wsRef.current = ws;
        setWsStatus('connecting');

        ws.onopen = () => {
          console.log(`[LiveChart] WebSocket connected for series ${seriesId}`);
          setWsStatus('connected');
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'data_point') {
              const newPoint: DataPoint = {
                timestamp: message.timestamp,
                elapsed_seconds: message.elapsed_seconds || 0,
                measurements: message.measurements
              };

              setDataPoints((prev) => {
                const updated = [...prev, newPoint];
                // Keep only the last maxPoints
                if (updated.length > maxPoints) {
                  return updated.slice(-maxPoints);
                }
                return updated;
              });
            }
          } catch (err) {
            console.error('[LiveChart] Failed to parse WebSocket message:', err);
          }
        };

        ws.onerror = (error) => {
          console.error('[LiveChart] WebSocket error:', error);
          setWsStatus('disconnected');
        };

        ws.onclose = () => {
          console.log('[LiveChart] WebSocket closed, reconnecting...');
          setWsStatus('disconnected');
          wsRef.current = null;
          // Reconnect after 2 seconds
          reconnectTimer = setTimeout(connect, 2000);
        };
      } catch (err) {
        console.error('[LiveChart] Failed to create WebSocket:', err);
        setWsStatus('disconnected');
        reconnectTimer = setTimeout(connect, 2000);
      }
    }

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
    };
  }, [seriesId, apiBase, isActive]);

  // Generate chart options
  const chartOptions = React.useMemo(() => {
    if (dataPoints.length === 0) {
      return {
        title: {
          text: 'Waiting for data...',
          left: 'center',
          top: 'center',
          textStyle: {
            fontSize: 16,
            color: '#999'
          }
        }
      } as any;
    }

    // Extract time series for each channel
    const timeData = dataPoints.map(dp => dp.elapsed_seconds);
    const series: any[] = [];

    channels.forEach((channel, idx) => {
      const channelKey = `${channel.device_id}_${channel.class_name}_${channel.channel}_${channel.method_name}`;
      const valueData = dataPoints.map(dp => {
        const value = dp.measurements[channelKey];
        return value !== undefined ? value : null;
      });

      const label = channel.label || `${channel.device_id} ${channel.method_name}`;

      series.push({
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
        text: 'Live Recording Data',
        left: 'center',
        textStyle: {
          fontSize: 18,
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
          let tooltip = `<b>Time: ${time.toFixed(2)}s</b><br/>`;
          params.forEach((param: any) => {
            if (param.value !== null) {
              tooltip += `${param.marker} ${param.seriesName}: ${param.value}<br/>`;
            }
          });
          return tooltip;
        }
      },
      legend: {
        data: series.map(s => s.name),
        top: 30,
        type: 'scroll'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
        top: 80
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: timeData,
        name: 'Time (s)',
        nameLocation: 'middle',
        nameGap: 30,
        axisLabel: {
          formatter: (value: number) => value.toFixed(1)
        }
      },
      yAxis: {
        type: 'value',
        name: 'Value',
        nameLocation: 'middle',
        nameGap: 50
      },
      series: series,
      animation: false, // Disable animation for better performance with live data
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
            name: `recording_${seriesId}_live`
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
  }, [dataPoints, channels, seriesId]);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: '400px', position: 'relative' }}>
      <div style={{
        position: 'absolute',
        top: 10,
        right: 10,
        padding: '5px 10px',
        borderRadius: '4px',
        background: wsStatus === 'connected' ? '#52c41a' : '#ff4d4f',
        color: 'white',
        fontSize: '12px',
        fontWeight: 'bold',
        zIndex: 10
      }}>
        {wsStatus === 'connected' ? '● LIVE' : wsStatus === 'connecting' ? '○ Connecting...' : '○ Disconnected'}
      </div>
      <ReactECharts
        option={chartOptions}
        style={{ height: '100%', width: '100%' }}
        notMerge={false}
        lazyUpdate={true}
      />
      <div style={{
        textAlign: 'center',
        marginTop: '10px',
        fontSize: '12px',
        color: '#666'
      }}>
        Points: {dataPoints.length} | Showing last {maxPoints} points
      </div>
    </div>
  );
};
