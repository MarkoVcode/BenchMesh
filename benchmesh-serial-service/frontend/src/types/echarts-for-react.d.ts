declare module 'echarts-for-react' {
  import { EChartsOption } from 'echarts';
  import * as React from 'react';

  export interface ReactEChartsProps {
    option: EChartsOption;
    style?: React.CSSProperties;
    settings?: object;
    loading?: boolean;
    theme?: string | object;
    onChartReady?: (instance: any) => void;
    onEvents?: object;
    notMerge?: boolean;
    lazyUpdate?: boolean;
    opts?: {
      devicePixelRatio?: number;
      renderer?: 'canvas' | 'svg';
      width?: number | string;
      height?: number | string;
    };
  }

  export default class ReactECharts extends React.Component<ReactEChartsProps> {
    getEchartsInstance(): any;
  }
}
