import React, { useEffect, useRef, memo } from 'react';

function TradingViewWidget({ symbol = 'BTCUSDT', interval = '15' }) {
    const containerRef = useRef(null);

    useEffect(() => {
        if (!containerRef.current) return;

        // Clear previous widget
        containerRef.current.innerHTML = '';

        // Convert interval format: '15m' -> '15', '1h' -> '60', '4h' -> '240', '1d' -> 'D'
        const intervalMap = {
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '1h': '60',
            '4h': '240',
            '1d': 'D'
        };
        const tvInterval = intervalMap[interval] || '15';

        // Format symbol for TradingView: BTCUSDT -> BINANCE:BTCUSDT.P (futures)
        const tvSymbol = `BINANCE:${symbol}.P`;

        const script = document.createElement('script');
        script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
        script.type = 'text/javascript';
        script.async = true;
        script.innerHTML = JSON.stringify({
            autosize: true,
            symbol: tvSymbol,
            interval: tvInterval,
            timezone: "Asia/Seoul",
            theme: "dark",
            style: "1",
            locale: "kr",
            enable_publishing: false,
            backgroundColor: "#000000",
            gridColor: "rgba(30, 30, 30, 0.6)",
            hide_top_toolbar: false,
            hide_legend: false,
            hide_side_toolbar: false,
            allow_symbol_change: false,
            save_image: false,
            hide_volume: false,
            withdateranges: true,
            details: false,
            hotlist: false,
            calendar: false,
            support_host: "https://www.tradingview.com",
            overrides: {
                "paneProperties.background": "#000000",
                "paneProperties.backgroundType": "solid",
                "paneProperties.vertGridProperties.color": "#1a1a1a",
                "paneProperties.horzGridProperties.color": "#1a1a1a",
                "scalesProperties.backgroundColor": "#000000",
                "scalesProperties.lineColor": "#1a1a1a",
                "scalesProperties.textColor": "#666666"
            },
            studies: [
                "MASimple@tv-basicstudies",
                "MASimple@tv-basicstudies",
                "MASimple@tv-basicstudies",
                "BB@tv-basicstudies",
                "RSI@tv-basicstudies"
            ],
            studies_overrides: {
                "MASimple@tv-basicstudies.0.length": 5,
                "MASimple@tv-basicstudies.0.linewidth": 1,
                "MASimple@tv-basicstudies.1.length": 10,
                "MASimple@tv-basicstudies.1.linewidth": 1,
                "MASimple@tv-basicstudies.2.length": 20,
                "MASimple@tv-basicstudies.2.linewidth": 2,
                "BB@tv-basicstudies.length": 20,
                "RSI@tv-basicstudies.length": 14
            }
        });

        const widgetContainer = document.createElement('div');
        widgetContainer.className = 'tradingview-widget-container__widget';
        widgetContainer.style.height = '100%';
        widgetContainer.style.width = '100%';

        containerRef.current.appendChild(widgetContainer);
        containerRef.current.appendChild(script);

        return () => {
            if (containerRef.current) {
                containerRef.current.innerHTML = '';
            }
        };
    }, [symbol, interval]);

    return (
        <div
            ref={containerRef}
            className="tradingview-widget-container"
            style={{
                height: '100%',
                width: '100%',
                background: '#000'
            }}
        />
    );
}

export default memo(TradingViewWidget);
