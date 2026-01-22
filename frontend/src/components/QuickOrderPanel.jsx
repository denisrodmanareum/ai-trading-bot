import React, { useState, useEffect } from 'react';

/**
 * OKX-Style Quick Order Panel
 * 원클릭 빠른 주문 패널
 */
function QuickOrderPanel({ symbol = 'BTCUSDT', currentPrice = 0 }) {
  const [orderType, setOrderType] = useState('LIMIT'); // LIMIT, MARKET
  const [side, setSide] = useState('BUY'); // BUY, SELL
  const [leverage, setLeverage] = useState(10);
  const [price, setPrice] = useState(currentPrice);
  const [quantity, setQuantity] = useState('');
  const [total, setTotal] = useState(0);
  const [percentage, setPercentage] = useState(0);

  useEffect(() => {
    if (orderType === 'MARKET') {
      setPrice(currentPrice);
    }
  }, [currentPrice, orderType]);

  useEffect(() => {
    if (quantity && price) {
      setTotal(parseFloat(quantity) * parseFloat(price));
    }
  }, [quantity, price]);

  const handlePercentageClick = (pct) => {
    setPercentage(pct);
    // Calculate quantity based on percentage of available balance
    // This is a simplified example
    const estimatedQty = (pct / 100) * 0.1; // Placeholder
    setQuantity(estimatedQty.toFixed(4));
  };

  const handleSubmitOrder = async () => {
    try {
      const orderData = {
        symbol,
        side,
        order_type: orderType,
        quantity: parseFloat(quantity),
        price: orderType === 'LIMIT' ? parseFloat(price) : null,
        leverage
      };

      const response = await fetch('/api/trading/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
      });

      if (response.ok) {
        alert(`✅ Order submitted: ${side} ${quantity} ${symbol}`);
        setQuantity('');
        setPercentage(0);
      } else {
        const error = await response.json();
        alert(`❌ Order failed: ${error.detail}`);
      }
    } catch (e) {
      console.error('Order error:', e);
      alert('❌ Order failed');
    }
  };

  return (
    <div style={{
      background: '#0a0a0a',
      border: '1px solid #1a1a1a',
      borderRadius: '6px',
      padding: '16px',
      fontFamily: 'Inter, sans-serif'
    }}>
      {/* Header: Order Type Tabs */}
      <div style={{
        display: 'flex',
        gap: '8px',
        marginBottom: '16px',
        borderBottom: '1px solid #1a1a1a',
        paddingBottom: '12px'
      }}>
        {['LIMIT', 'MARKET'].map(type => (
          <button
            key={type}
            onClick={() => setOrderType(type)}
            style={{
              padding: '6px 16px',
              background: orderType === type ? '#222' : 'transparent',
              border: orderType === type ? '1px solid #333' : '1px solid transparent',
              borderRadius: '4px',
              color: orderType === type ? '#fff' : '#666',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '600',
              transition: 'all 0.2s'
            }}
          >
            {type}
          </button>
        ))}
      </div>

      {/* Leverage Selector */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ fontSize: '0.75rem', color: '#888', display: 'block', marginBottom: '8px' }}>
          Leverage: {leverage}x
        </label>
        <input
          type="range"
          min="1"
          max="125"
          value={leverage}
          onChange={(e) => setLeverage(parseInt(e.target.value))}
          style={{
            width: '100%',
            accentColor: '#00b07c'
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#555', marginTop: '4px' }}>
          <span>1x</span>
          <span>25x</span>
          <span>50x</span>
          <span>125x</span>
        </div>
      </div>

      {/* Price Input (for LIMIT orders) */}
      {orderType === 'LIMIT' && (
        <div style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '0.75rem', color: '#888', display: 'block', marginBottom: '8px' }}>
            Price (USDT)
          </label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              background: '#111',
              border: '1px solid #222',
              borderRadius: '4px',
              color: '#fff',
              fontSize: '0.85rem',
              outline: 'none'
            }}
            placeholder={currentPrice.toFixed(2)}
          />
        </div>
      )}

      {/* Quantity Input */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ fontSize: '0.75rem', color: '#888', display: 'block', marginBottom: '8px' }}>
          Amount (BTC)
        </label>
        <input
          type="number"
          value={quantity}
          onChange={(e) => {
            setQuantity(e.target.value);
            setPercentage(0);
          }}
          style={{
            width: '100%',
            padding: '10px 12px',
            background: '#111',
            border: '1px solid #222',
            borderRadius: '4px',
            color: '#fff',
            fontSize: '0.85rem',
            outline: 'none'
          }}
          placeholder="0.0000"
        />
      </div>

      {/* Percentage Buttons */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '8px',
        marginBottom: '16px'
      }}>
        {[25, 50, 75, 100].map(pct => (
          <button
            key={pct}
            onClick={() => handlePercentageClick(pct)}
            style={{
              padding: '8px',
              background: percentage === pct ? '#222' : '#111',
              border: percentage === pct ? '1px solid #00b07c' : '1px solid #222',
              borderRadius: '4px',
              color: percentage === pct ? '#00b07c' : '#888',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: '600',
              transition: 'all 0.2s'
            }}
          >
            {pct}%
          </button>
        ))}
      </div>

      {/* Total */}
      <div style={{
        padding: '12px',
        background: '#111',
        borderRadius: '4px',
        marginBottom: '16px',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.8rem'
      }}>
        <span style={{ color: '#888' }}>Total:</span>
        <span style={{ color: '#fff', fontWeight: '700' }}>
          {total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDT
        </span>
      </div>

      {/* Buy/Sell Buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <button
          onClick={() => {
            setSide('BUY');
            handleSubmitOrder();
          }}
          style={{
            padding: '14px',
            background: 'linear-gradient(135deg, #00b07c, #00d98e)',
            border: 'none',
            borderRadius: '6px',
            color: '#fff',
            fontSize: '0.9rem',
            fontWeight: '800',
            cursor: 'pointer',
            transition: 'all 0.2s',
            boxShadow: '0 4px 12px rgba(0, 176, 124, 0.3)'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 6px 16px rgba(0, 176, 124, 0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 176, 124, 0.3)';
          }}
        >
          BUY / LONG
        </button>
        <button
          onClick={() => {
            setSide('SELL');
            handleSubmitOrder();
          }}
          style={{
            padding: '14px',
            background: 'linear-gradient(135deg, #ff4b4b, #ff6b6b)',
            border: 'none',
            borderRadius: '6px',
            color: '#fff',
            fontSize: '0.9rem',
            fontWeight: '800',
            cursor: 'pointer',
            transition: 'all 0.2s',
            boxShadow: '0 4px 12px rgba(255, 75, 75, 0.3)'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 6px 16px rgba(255, 75, 75, 0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(255, 75, 75, 0.3)';
          }}
        >
          SELL / SHORT
        </button>
      </div>

      {/* Risk Info */}
      <div style={{
        marginTop: '16px',
        padding: '12px',
        background: '#111',
        border: '1px solid #222',
        borderRadius: '4px',
        fontSize: '0.7rem',
        color: '#666'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span>Entry Price:</span>
          <span style={{ color: '#fff' }}>{(orderType === 'MARKET' ? currentPrice : price).toLocaleString()}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span>Margin Required:</span>
          <span style={{ color: '#fff' }}>{(total / leverage).toFixed(2)} USDT</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Liquidation Price:</span>
          <span style={{ color: '#ff4b4b' }}>
            {side === 'BUY' 
              ? (currentPrice * (1 - 0.9 / leverage)).toFixed(2)
              : (currentPrice * (1 + 0.9 / leverage)).toFixed(2)
            }
          </span>
        </div>
      </div>
    </div>
  );
}

export default QuickOrderPanel;
