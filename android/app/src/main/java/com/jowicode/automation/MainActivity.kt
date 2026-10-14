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
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
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
    var apiToken by remember { mutableStateOf("") }
    var topic by remember { mutableStateOf("") }
    var connectionState by remember { mutableStateOf("Not connected") }
    var statusDetails by remember { mutableStateOf("Enter your deployed HTTPS backend URL and access token. The token stays in memory for this screen only.") }
    var jobsDetails by remember { mutableStateOf("No job list loaded yet.") }
    var isBusy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val baseUrl = backendUrl.trim().trimEnd('/')
    val canCallApi = baseUrl.startsWith("https://") && apiToken.isNotBlank()

    fun runRequest(action: suspend () -> Pair<String, String>) {
        if (isBusy) return
        isBusy = true
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                try { action() } catch (e: Exception) {
                    "Request failed" to (e.message ?: "Check network, URL, and backend configuration.")
                }
            }
            connectionState = result.first
            statusDetails = result.second
            isBusy = false
        }
    }

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Text("THE JOWI CODE", style = MaterialTheme.typography.labelLarge)
                Text("Automation dashboard", style = MaterialTheme.typography.headlineMedium)
                Text("Manage the development queue from your phone. Video generation and public publishing are not enabled.")

                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Backend connection", style = MaterialTheme.typography.titleMedium)
                        OutlinedTextField(
                            value = backendUrl,
                            onValueChange = { backendUrl = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Backend HTTPS URL") },
                            placeholder = { Text("https://your-service.onrender.com") },
                            singleLine = true
                        )
                        OutlinedTextField(
                            value = apiToken,
                            onValueChange = { apiToken = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Backend access token") },
                            visualTransformation = PasswordVisualTransformation(),
                            singleLine = true
                        )
                        Button(
                            enabled = !isBusy && baseUrl.startsWith("https://"),
                            onClick = {
                                runRequest {
                                    val health = request(baseUrl, "/health", null)
                                    if (health.first !in 200..299) {
                                        "Backend error" to "Health check returned HTTP ${health.first}."
                                    } else if (apiToken.isBlank()) {
                                        "Connected" to "Health check passed. Enter the access token to view protected status and queue jobs."
                                    } else {
                                        val protected = request(baseUrl, "/api/status", apiToken)
                                        if (protected.first in 200..299) {
                                            val body = JSONObject(protected.second)
                                            "Connected" to "API authenticated. Publishing enabled: ${body.optBoolean("publishing_enabled", false)}. Video provider configured: ${body.optBoolean("video_generation_configured", false)}. YouTube OAuth configured: ${body.optBoolean("youtube_oauth_configured", false)}."
                                        } else {
                                            "Authentication failed" to "Protected status returned HTTP ${protected.first}. Verify the access token and backend environment."
                                        }
                                    }
                                }
                            }
                        ) { Text(if (isBusy) "Working…" else "Check and authenticate") }
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
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Create a Shorts job", style = MaterialTheme.typography.titleMedium)
                        OutlinedTextField(
                            value = topic,
                            onValueChange = { topic = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Short topic") },
                            placeholder = { Text("Discipline, focus, building your future…") },
                            singleLine = true
                        )
                        Button(
                            enabled = !isBusy && canCallApi && topic.trim().length >= 3,
                            onClick = {
                                val submittedTopic = topic.trim()
                                runRequest {
                                    val result = request(
                                        baseUrl, "/api/jobs",
                                        apiToken,
                                        JSONObject().put("job_type", "short_video").put("topic", submittedTopic).toString()
                                    )
                                    if (result.first == 202) {
                                        "Job queued" to "Job ID: ${JSONObject(result.second).optString("id")}. This only queues the request; a full media worker is not yet connected."
                                    } else {
                                        "Could not queue job" to "HTTP ${result.first}: ${safeError(result.second)}"
                                    }
                                }
                            }
                        ) { Text("Queue Short") }
                        Button(
                            enabled = !isBusy && canCallApi,
                            onClick = {
                                runRequest {
                                    val result = request(baseUrl, "/api/jobs", apiToken)
                                    if (result.first in 200..299) {
                                        val list = JSONObject(result.second).optJSONArray("jobs")
                                        val lines = if (list == null || list.length() == 0) "No jobs yet." else (0 until list.length()).joinToString("\n") { i ->
                                            val job = list.getJSONObject(i)
                                            buildString {
                                                append("${job.optString("status").uppercase()} — ${job.optString("topic")}")
                                                append("\nUpdated: ${job.optString("updated_at_utc", "not recorded")}")
                                                val error = job.optString("error")
                                                if (error.isNotBlank() && error != "null") append("\nNote: $error")
                                                append("\nID: ${job.optString("id")}")
                                            }
                                        }
                                        jobsDetails = lines
                                        "Queue refreshed" to "Loaded ${list?.length() ?: 0} job(s)."
                                    } else {
                                        "Could not load jobs" to "HTTP ${result.first}: ${safeError(result.second)}"
                                    }
                                }
                            }
                        ) { Text("Refresh job list") }
                        Text(jobsDetails, style = MaterialTheme.typography.bodySmall)
                    }
                }

                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Pipeline readiness", style = MaterialTheme.typography.titleMedium)
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Daily target"); Text("2–3 Shorts")
                        }
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Public publishing"); Text("Disabled")
                        }
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Current build"); Text("Development scaffold")
                        }
                    }
                }
                Text(
                    "Security: the token is not saved to disk and is cleared when this screen is recreated. Do not share it. Queueing a job does not generate a video yet.",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

private fun request(
    baseUrl: String,
    path: String,
    bearerToken: String?,
    body: String? = null
): Pair<Int, String> {
    var connection: HttpURLConnection? = null
    return try {
        connection = (URL("$baseUrl$path").openConnection() as HttpURLConnection).apply {
            requestMethod = if (body == null) "GET" else "POST"
            connectTimeout = 10000
            readTimeout = 15000
            setRequestProperty("Accept", "application/json")
            if (!bearerToken.isNullOrBlank()) setRequestProperty("Authorization", "Bearer $bearerToken")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        if (body != null) connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        code to response
    } finally {
        connection?.disconnect()
    }
}

private fun safeError(response: String): String {
    return try { JSONObject(response).optString("detail", "Request was rejected.") }
    catch (_: Exception) { "Request was rejected." }
}
