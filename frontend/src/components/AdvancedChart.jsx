import React, { useEffect, useRef, memo, useState } from 'react';
import { createChart } from 'lightweight-charts';

// Technical Indicator Calculations
const calculateSMA = (data, period) => {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            result.push({ time: data[i].time, value: null });
        } else {
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j].close;
            }
            result.push({ time: data[i].time, value: sum / period });
        }
    }
    return result.filter(d => d.value !== null);
};

const calculateBollingerBands = (data, period = 20, stdDev = 2) => {
    const upper = [];
    const middle = [];
    const lower = [];

    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) continue;

        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        const sma = sum / period;

        let variance = 0;
        for (let j = 0; j < period; j++) {
            variance += Math.pow(data[i - j].close - sma, 2);
        }
        const std = Math.sqrt(variance / period);

        middle.push({ time: data[i].time, value: sma });
        upper.push({ time: data[i].time, value: sma + std * stdDev });
        lower.push({ time: data[i].time, value: sma - std * stdDev });
    }

    return { upper, middle, lower };
};

const calculateRSI = (data, period = 14) => {
    const result = [];
    let gains = 0;
    let losses = 0;

    for (let i = 1; i < data.length; i++) {
        const change = data[i].close - data[i - 1].close;

        if (i <= period) {
            if (change > 0) gains += change;
            else losses += Math.abs(change);

            if (i === period) {
                const avgGain = gains / period;
                const avgLoss = losses / period;
                const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
                const rsi = 100 - (100 / (1 + rs));
                result.push({ time: data[i].time, value: rsi });
            }
        } else {
            const prevResult = result[result.length - 1];
            const currentGain = change > 0 ? change : 0;
            const currentLoss = change < 0 ? Math.abs(change) : 0;

            const avgGain = (gains * (period - 1) + currentGain) / period;
            const avgLoss = (losses * (period - 1) + currentLoss) / period;
            gains = avgGain;
            losses = avgLoss;

            const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
            const rsi = 100 - (100 / (1 + rs));
            result.push({ time: data[i].time, value: rsi });
        }
    }

    return result;
};

function AdvancedChart({ symbol = 'BTCUSDT', interval = '15m', hideRSI = false }) {
    const chartContainerRef = useRef(null);
    const rsiContainerRef = useRef(null);
    const chartRef = useRef(null);
    const rsiChartRef = useRef(null);

    // Ensure interval is always a valid string
    const safeInterval = (typeof interval === 'string' && interval) ? interval : '15m';

    const [showIndicators, setShowIndicators] = useState({
        ma5: true,
        ma20: true,
        ma60: true,
        ma120: true,
        bb: true,
        rsi: !hideRSI
    });
    const [layoutTick, setLayoutTick] = useState(0);

    useEffect(() => {
        let disposed = false;
        let abortController = null;
        let retryTimer = null;

        const container = chartContainerRef.current;
        if (!container) return;

        // Validate interval before proceeding
        if (typeof safeInterval !== 'string' || !safeInterval) {
            console.error('Invalid interval:', interval);
            return;
        }

        // Wait until container has non-zero width (common during initial layout / tab switches)
        if ((container.clientWidth || 0) === 0) {
            retryTimer = setTimeout(() => {
                if (!disposed) setLayoutTick((t) => t + 1);
            }, 100);
            return () => {
                disposed = true;
                if (retryTimer) clearTimeout(retryTimer);
            };
        }

        // Main Chart
        const initialWidth = container.clientWidth || 600;
        const initialHeight = container.clientHeight || 300;

        const chart = createChart(container, {
            layout: {
                background: { type: 'solid', color: '#000000' },
                textColor: '#666',
                fontSize: 11,
                fontFamily: 'Inter, sans-serif'
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: 'rgba(255,255,255,0.03)' }
            },
            width: initialWidth,
            height: initialHeight,
            timeScale: {
                borderColor: '#111',
                timeVisible: true,
                secondsVisible: false
            },
            rightPriceScale: {
                borderColor: '#111',
                scaleMargins: { top: 0.1, bottom: 0.15 }
            },
            crosshair: {
                mode: 1,
                vertLine: { width: 1, color: 'rgba(255,255,255,0.2)', style: 3, labelBackgroundColor: '#222' },
                horzLine: { width: 1, color: 'rgba(255,255,255,0.2)', style: 3, labelBackgroundColor: '#222' }
            },
            handleScroll: { mouseWheel: true, pressedMouseMove: true },
            handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true }
        });

        // Candlestick Series
        const candleSeries = chart.addCandlestickSeries({
            upColor: '#00b07c',
            downColor: '#ff5b5b',
            borderVisible: false,
            wickUpColor: '#00b07c',
            wickDownColor: '#ff5b5b'
        });

        // Volume Series
        const volumeSeries = chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume',
            scaleMargins: { top: 0.85, bottom: 0 }
        });
        chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

        // MA Lines
        const ma5Series = chart.addLineSeries({ color: '#f6c343', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        const ma20Series = chart.addLineSeries({ color: '#5dade2', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        const ma60Series = chart.addLineSeries({ color: '#bb8fce', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        const ma120Series = chart.addLineSeries({ color: '#e67e22', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });

        // Bollinger Bands
        const bbUpperSeries = chart.addLineSeries({ color: 'rgba(100, 100, 255, 0.5)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        const bbMiddleSeries = chart.addLineSeries({ color: 'rgba(100, 100, 255, 0.3)', lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
        const bbLowerSeries = chart.addLineSeries({ color: 'rgba(100, 100, 255, 0.5)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });

        // RSI Chart
        let rsiChart = null;
        let rsiSeries = null;
        if (rsiContainerRef.current && showIndicators.rsi) {
            rsiChart = createChart(rsiContainerRef.current, {
                layout: {
                    background: { type: 'solid', color: '#000000' },
                    textColor: '#666',
                    fontSize: 10,
                    fontFamily: 'Inter, sans-serif'
                },
                grid: {
                    vertLines: { visible: false },
                    horzLines: { color: 'rgba(255,255,255,0.03)' }
                },
                width: rsiContainerRef.current.clientWidth || 600,
                height: rsiContainerRef.current.clientHeight || 80,
                timeScale: { borderColor: '#111', visible: false },
                rightPriceScale: { borderColor: '#111', scaleMargins: { top: 0.1, bottom: 0.1 } },
                crosshair: { mode: 0 }
            });

            rsiSeries = rsiChart.addLineSeries({
                color: '#e74c3c',
                lineWidth: 1,
                priceLineVisible: false,
                lastValueVisible: true
            });

            // RSI Overbought/Oversold lines
            rsiChart.addLineSeries({ color: 'rgba(255,255,255,0.1)', lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false })
                .setData([{ time: 0, value: 70 }, { time: 9999999999, value: 70 }]);
            rsiChart.addLineSeries({ color: 'rgba(255,255,255,0.1)', lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false })
                .setData([{ time: 0, value: 30 }, { time: 9999999999, value: 30 }]);

            rsiChartRef.current = rsiChart;
        }

        chartRef.current = chart;

        // Fetch and update data
        const fetchData = async () => {
            try {
                if (disposed) return;
                // Ensure interval is a valid string
                const validInterval = (typeof interval === 'string' && interval) ? interval : '15m';
                abortController?.abort();
                abortController = new AbortController();
                const res = await fetch(`/api/dashboard/chart-data/${symbol}?interval=${validInterval}&limit=200`, {
                    signal: abortController.signal
                });
                if (!res.ok) return;

                const json = await res.json();
                if (disposed) return;
                const data = json.data.map(d => ({
                    time: d.timestamp / 1000 + 32400,
                    open: d.open,
                    high: d.high,
                    low: d.low,
                    close: d.close,
                    volume: d.volume
                })).sort((a, b) => a.time - b.time);

                // Update candlesticks
                candleSeries.setData(data);

                // Update volume
                volumeSeries.setData(data.map(d => ({
                    time: d.time,
                    value: d.volume,
                    color: d.close >= d.open ? 'rgba(0, 176, 124, 0.4)' : 'rgba(255, 91, 91, 0.4)'
                })));

                // Update MA lines
                if (showIndicators.ma5) ma5Series.setData(calculateSMA(data, 5));
                if (showIndicators.ma20) ma20Series.setData(calculateSMA(data, 20));
                if (showIndicators.ma60) ma60Series.setData(calculateSMA(data, 60));
                if (showIndicators.ma120) ma120Series.setData(calculateSMA(data, 120));

                // Update Bollinger Bands
                if (showIndicators.bb) {
                    const bb = calculateBollingerBands(data, 20, 2);
                    bbUpperSeries.setData(bb.upper);
                    bbMiddleSeries.setData(bb.middle);
                    bbLowerSeries.setData(bb.lower);
                }

                // Update RSI
                if (showIndicators.rsi && rsiSeries) {
                    rsiSeries.setData(calculateRSI(data, 14));
                }

                // Sync time scales
                if (rsiChart) {
                    // subscribe once (guarded by effect lifetime)
                    chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
                        if (!disposed && range) rsiChart.timeScale().setVisibleRange(range);
                    });
                }

            } catch (e) {
                if (e?.name !== 'AbortError') {
                    console.error('Chart data error:', e);
                }
            }
        };

        fetchData();
        const dataInterval = setInterval(fetchData, 5000);

        // Resize handler
        const handleResize = () => {
            if (disposed) return;
            if (chartContainerRef.current) {
                chart.applyOptions({
                    width: chartContainerRef.current.clientWidth || initialWidth,
                    height: chartContainerRef.current.clientHeight || initialHeight
                });
            }
            if (rsiContainerRef.current && rsiChart) {
                rsiChart.applyOptions({
                    width: rsiContainerRef.current.clientWidth || initialWidth,
                    height: rsiContainerRef.current.clientHeight || 80
                });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            disposed = true;
            clearInterval(dataInterval);
            window.removeEventListener('resize', handleResize);
            abortController?.abort();
            try { chart.remove(); } catch (_) {}
            try { if (rsiChart) rsiChart.remove(); } catch (_) {}
        };
    }, [symbol, safeInterval, showIndicators, layoutTick]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#000' }}>
            {/* Indicator Legend */}
            <div style={{
                display: 'flex',
                gap: '1rem',
                padding: '0.5rem 1rem',
                background: '#000',
                borderBottom: '1px solid #111',
                fontSize: '0.65rem',
                fontWeight: '700',
                flexWrap: 'wrap'
            }}>
                <span style={{ color: '#f6c343' }}>● MA5</span>
                <span style={{ color: '#5dade2' }}>● MA20</span>
                <span style={{ color: '#bb8fce' }}>● MA60</span>
                <span style={{ color: '#e67e22' }}>● MA120</span>
                <span style={{ color: 'rgba(100, 100, 255, 0.7)' }}>● BB(20,2)</span>
                {!hideRSI && <span style={{ color: '#e74c3c' }}>● RSI(14)</span>}
            </div>

            {/* Main Chart */}
            <div
                ref={chartContainerRef}
                style={{ flex: 1, minHeight: '300px' }}
            />

            {/* RSI Panel */}
            {showIndicators.rsi && (
                <div style={{
                    borderTop: '1px solid #111',
                    background: '#000'
                }}>
                    <div style={{
                        padding: '0.25rem 1rem',
                        fontSize: '0.6rem',
                        fontWeight: '800',
                        color: '#444',
                        textTransform: 'uppercase'
                    }}>
                        RSI (14)
                    </div>
                    <div
                        ref={rsiContainerRef}
                        style={{ height: '80px' }}
                    />
                </div>
            )}
        </div>
    );
}

export default memo(AdvancedChart);
