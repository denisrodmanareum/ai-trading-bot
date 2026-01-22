package com.riot91.aitrading

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.riot91.aitrading.databinding.ActivityMainBinding
import com.riot91.aitrading.network.ApiClient
import com.riot91.aitrading.network.WebSocketManager
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private lateinit var apiClient: ApiClient
    private lateinit var wsManager: WebSocketManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Initialize API client
        apiClient = ApiClient()
        wsManager = WebSocketManager()
        
        setupUI()
        fetchDashboardData()
        connectWebSocket()
    }
    
    private fun setupUI() {
        binding.btnRefresh.setOnClickListener {
            fetchDashboardData()
        }
        
        binding.btnEmergencyStop.setOnClickListener {
            emergencyStop()
        }
    }
    
    private fun fetchDashboardData() {
        lifecycleScope.launch {
            try {
                val overview = apiClient.getDashboardOverview()
                updateUI(overview)
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Failed to fetch data", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun updateUI(overview: DashboardOverview) {
        binding.apply {
            tvBalance.text = "$${overview.account.balance}"
            tvPnl.text = "$${overview.totalUnrealizedPnl}"
            tvPositions.text = overview.positions.size.toString()
            
            // Update PnL color
            if (overview.totalUnrealizedPnl >= 0) {
                tvPnl.setTextColor(getColor(R.color.green))
            } else {
                tvPnl.setTextColor(getColor(R.color.red))
            }
        }
    }
    
    private fun connectWebSocket() {
        wsManager.connect("ws://YOUR_SERVER:8000/ws/prices") { message ->
            runOnUiThread {
                // Update real-time price
                binding.tvBtcPrice.text = "$${message.close}"
            }
        }
    }
    
    private fun emergencyStop() {
        lifecycleScope.launch {
            try {
                apiClient.closeAllPositions()
                Toast.makeText(this@MainActivity, "All positions closed!", Toast.LENGTH_SHORT).show()
                fetchDashboardData()
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Failed to close positions", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        wsManager.disconnect()
    }
}

// Data classes
data class DashboardOverview(
    val account: Account,
    val positions: List<Position>,
    val totalUnrealizedPnl: Double
)

data class Account(
    val balance: Double,
    val availableBalance: Double
)

data class Position(
    val symbol: String,
    val positionAmt: Double,
    val unrealizedPnl: Double
)
