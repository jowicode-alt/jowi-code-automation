package com.jowicode.automation

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { Dashboard() }
    }
}

@androidx.compose.runtime.Composable
private fun Dashboard() {
    var backendUrl by remember { mutableStateOf("") }
    var connectionState by remember { mutableStateOf("Not connected") }
    var statusDetails by remember { mutableStateOf("Backend publishing is disabled until setup and readiness checks are complete.") }
    var isChecking by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Text("THE JOWI CODE", style = MaterialTheme.typography.labelLarge)
                Text("Automation dashboard", style = MaterialTheme.typography.headlineMedium)
                Text("Manage your Shorts workflow from your phone. Publishing is not enabled in this development build.")

                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Backend connection", style = MaterialTheme.typography.titleMedium)
                        OutlinedTextField(
                            value = backendUrl,
                            onValueChange = { backendUrl = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Backend HTTPS URL") },
                            placeholder = { Text("https://your-service.example") },
                            singleLine = true
                        )
                        Button(
                            enabled = !isChecking && backendUrl.trim().startsWith("https://"),
                            onClick = {
                                isChecking = true
                                connectionState = "Checking…"
                                scope.launch {
                                    val result = withContext(Dispatchers.IO) { checkHealth(backendUrl.trim().trimEnd('/')) }
                                    connectionState = result.first
                                    statusDetails = result.second
                                    isChecking = false
                                }
                            }
                        ) { Text(if (isChecking) "Checking…" else "Check backend") }
                    }
                }

                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Connection status", style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.height(6.dp))
                        Text(connectionState, style = MaterialTheme.typography.titleLarge)
                        Spacer(Modifier.height(4.dp))
                        Text(statusDetails)
                    }
                }

                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Pipeline status", style = MaterialTheme.typography.titleMedium)
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Daily target")
                            Text("2–3 Shorts")
                        }
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Auto-publishing")
                            Text("Disabled")
                        }
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Release")
                            Text("Development")
                        }
                    }
                }
                Text("Never enter API keys or OAuth secrets into this app. Secure sign-in and authenticated control endpoints must be implemented before live controls are added.", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

private fun checkHealth(baseUrl: String): Pair<String, String> {
    var connection: HttpURLConnection? = null
    return try {
        connection = (URL("$baseUrl/health").openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 8000
            readTimeout = 8000
        }
        if (connection.responseCode in 200..299) {
            "Connected" to "The backend health endpoint responded successfully. Publishing remains disabled."
        } else {
            "Backend error" to "Health check returned HTTP ${connection.responseCode}."
        }
    } catch (e: Exception) {
        "Connection failed" to (e.message ?: "Could not reach the backend. Check the HTTPS URL and network.")
    } finally {
        connection?.disconnect()
    }
}
