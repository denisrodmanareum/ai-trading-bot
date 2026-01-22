import React, { useState, useEffect, useRef } from 'react';

/**
 * OKX-Style Real-time Order Book
 * 실시간 오더북 with 부드러운 바 애니메이션
 */
function OrderBook({ symbol = 'BTCUSDT', onPriceClick }) {
  const [orderBook, setOrderBook] = useState({ bids: [], asks: [] });
  const [spread, setSpread] = useState(0);
  const [spreadPercent, setSpreadPercent] = useState(0);
  const wsRef = useRef(null);

  useEffect(() => {
    // Binance WebSocket for Order Book
    const connectWebSocket = () => {
      const ws = new WebSocket(
        `wss://fstream.binance.com/ws/${symbol.toLowerCase()}@depth20@100ms`
      );

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // Format bids and asks
        const bids = data.b.slice(0, 15).map(([price, qty]) => ({
          price: parseFloat(price),
          quantity: parseFloat(qty),
          total: parseFloat(price) * parseFloat(qty)
        }));

        const asks = data.a.slice(0, 15).map(([price, qty]) => ({
          price: parseFloat(price),
          quantity: parseFloat(qty),
          total: parseFloat(price) * parseFloat(qty)
        }));

        // Calculate spread
        if (bids.length > 0 && asks.length > 0) {
          const bestBid = bids[0].price;
          const bestAsk = asks[0].price;
          const spreadValue = bestAsk - bestBid;
          const spreadPct = (spreadValue / bestBid) * 100;

          setSpread(spreadValue);
          setSpreadPercent(spreadPct);
        }

        setOrderBook({ bids, asks });
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [symbol]);

  // Calculate max volume for bar width
  const maxBidVolume = Math.max(...orderBook.bids.map(b => b.quantity), 1);
  const maxAskVolume = Math.max(...orderBook.asks.map(a => a.quantity), 1);
  const maxVolume = Math.max(maxBidVolume, maxAskVolume);

  return (
    <div style={{
      background: '#0a0a0a',
      border: '1px solid #1a1a1a',
      borderRadius: '6px',
      overflow: 'hidden',
      fontFamily: 'monospace',
      height: '100%'
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #1a1a1a',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{
          fontSize: '0.85rem',
          fontWeight: '700',
          color: '#fff',
          letterSpacing: '0.02em'
        }}>
          Order Book
        </div>
        <div style={{ fontSize: '0.7rem', color: '#666' }}>
          Spread: {spread.toFixed(2)} ({spreadPercent.toFixed(3)}%)
        </div>
      </div>

      {/* Column Headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        padding: '8px 16px',
        fontSize: '0.65rem',
        color: '#666',
        fontWeight: '600',
        borderBottom: '1px solid #1a1a1a'
      }}>
        <div>Price (USDT)</div>
        <div style={{ textAlign: 'right' }}>Amount (BTC)</div>
        <div style={{ textAlign: 'right' }}>Total (USDT)</div>
      </div>

      <div style={{
        height: 'calc(100% - 120px)',
        overflowY: 'auto',
        scrollbarWidth: 'thin',
        scrollbarColor: '#333 #0a0a0a'
      }}>
        {/* Asks (Sell Orders) - Red */}
        <div style={{
          display: 'flex',
          flexDirection: 'column-reverse',
          padding: '4px 0'
        }}>
          {orderBook.asks.map((ask, idx) => {
            const widthPercent = (ask.quantity / maxVolume) * 100;
            return (
              <div
                key={`ask-${idx}`}
                style={{
                  position: 'relative',
                  padding: '4px 16px',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#1a0a0a'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                {/* Animated Background Bar */}
                <div style={{
                  position: 'absolute',
                  right: 0,
                  top: 0,
                  bottom: 0,
                  width: `${widthPercent}%`,
                  background: 'linear-gradient(90deg, transparent, rgba(255, 75, 75, 0.15))',
                  transition: 'width 0.3s ease-out',
                  zIndex: 0
                }} />

                <div
                  onClick={() => onPriceClick && onPriceClick(ask.price)}
                  style={{ color: '#ff4b4b', fontWeight: '600', zIndex: 1, cursor: 'pointer' }}>
                  {ask.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div style={{ textAlign: 'right', color: '#ccc', zIndex: 1 }}>
                  {ask.quantity.toFixed(4)}
                </div>
                <div style={{ textAlign: 'right', color: '#888', fontSize: '0.7rem', zIndex: 1 }}>
                  {ask.total.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Spread Indicator */}
        <div style={{
          padding: '12px 16px',
          background: '#111',
          borderTop: '1px solid #1a1a1a',
          borderBottom: '1px solid #1a1a1a',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          margin: '4px 0'
        }}>
          <div style={{ fontSize: '0.95rem', fontWeight: '800', color: '#00b07c' }}>
            {orderBook.bids[0]?.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '0.65rem', color: '#666' }}>
            ↕ {spread.toFixed(2)}
          </div>
          <div style={{ fontSize: '0.95rem', fontWeight: '800', color: '#ff4b4b' }}>
            {orderBook.asks[0]?.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>

        {/* Bids (Buy Orders) - Green */}
        <div style={{ padding: '4px 0' }}>
          {orderBook.bids.map((bid, idx) => {
            const widthPercent = (bid.quantity / maxVolume) * 100;
            return (
              <div
                key={`bid-${idx}`}
                style={{
                  position: 'relative',
                  padding: '4px 16px',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#0a1a0a'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                {/* Animated Background Bar */}
                <div style={{
                  position: 'absolute',
                  right: 0,
                  top: 0,
                  bottom: 0,
                  width: `${widthPercent}%`,
                  background: 'linear-gradient(90deg, transparent, rgba(0, 176, 124, 0.15))',
                  transition: 'width 0.3s ease-out',
                  zIndex: 0
                }} />

                <div
                  onClick={() => onPriceClick && onPriceClick(bid.price)}
                  style={{ color: '#00b07c', fontWeight: '600', zIndex: 1, cursor: 'pointer' }}>
                  {bid.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div style={{ textAlign: 'right', color: '#ccc', zIndex: 1 }}>
                  {bid.quantity.toFixed(4)}
                </div>
                <div style={{ textAlign: 'right', color: '#888', fontSize: '0.7rem', zIndex: 1 }}>
                  {bid.total.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default OrderBook;
