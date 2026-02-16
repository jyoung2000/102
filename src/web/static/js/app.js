// Wallpaper Scraper GUI — Vanilla JS SPA

let pollTimer = null;
let allJobs = [];
let currentSettings = {};

// --- Init ---
document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    loadHealth();
    loadSettings();
    loadBaserowConfig();
    loadJobs();
    loadStats();
});

// --- Tabs ---
function initTabs() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    const content = document.getElementById(`tab-${tabId}`);
    if (btn) btn.classList.add("active");
    if (content) content.classList.add("active");

    if (tabId === "jobs") loadJobs();
    if (tabId === "stats") loadStats();
    if (tabId === "settings") loadSettings();
}

// --- Health ---
async function loadHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();

        setDot("dot-browser", data.browser_ready ? "ok" : "err");
        setDot("dot-ai", data.ai_model_loaded ? "ok" : "err");
        setDot("dot-baserow", data.baserow_configured ? "ok" : "warn");

        // If Baserow not configured, show warning + auto-switch on first launch
        if (!data.baserow_configured) {
            document.getElementById("baserow-warning").style.display = "block";
            document.getElementById("btn-scrape").disabled = true;

            // First launch: check if we have any jobs, if not switch to Baserow tab
            const jobsRes = await fetch("/api/jobs");
            const jobs = await jobsRes.json();
            if (jobs.length === 0) {
                switchTab("baserow");
            }
        } else {
            document.getElementById("baserow-warning").style.display = "none";
            document.getElementById("btn-scrape").disabled = false;
        }
    } catch (e) {
        setDot("dot-browser", "err");
        setDot("dot-ai", "err");
        setDot("dot-baserow", "err");
    }
}

function setDot(id, status) {
    const dot = document.getElementById(id);
    if (dot) {
        dot.className = "status-dot " + status;
    }
}

// --- Scrape ---
async function startScrape() {
    const urlText = document.getElementById("scrape-urls").value.trim();
    if (!urlText) {
        toast("Enter at least one URL", "error");
        return;
    }

    const urls = urlText.split("\n").map(u => u.trim()).filter(u => u);
    if (urls.length === 0) {
        toast("Enter at least one valid URL", "error");
        return;
    }

    const maxPages = parseInt(document.getElementById("scrape-max-pages").value) || null;
    const minWidth = parseInt(document.getElementById("scrape-min-width").value) || null;
    const minHeight = parseInt(document.getElementById("scrape-min-height").value) || null;

    const ratios = [];
    document.querySelectorAll("#aspect-ratios input:checked").forEach(cb => {
        ratios.push(cb.value);
    });

    const body = { urls };
    if (maxPages) body.max_pages = maxPages;
    if (minWidth) body.min_width = minWidth;
    if (minHeight) body.min_height = minHeight;
    if (ratios.length > 0) body.aspect_ratios = ratios;

    const btn = document.getElementById("btn-scrape");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Submitting...';

    try {
        const res = await fetch("/api/scrape", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            const err = await res.json();
            toast(err.detail || "Failed to start scrape", "error");
            return;
        }

        const data = await res.json();
        toast(`Job ${data.job_id} started`, "success");
        document.getElementById("scrape-urls").value = "";
        loadJobs();
        startPolling();
    } catch (e) {
        toast("Network error: " + e.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = "Start Scraping";
    }
}

// --- Jobs ---
async function loadJobs() {
    try {
        const res = await fetch("/api/jobs");
        allJobs = await res.json();
        renderJobs();
        renderRecentJobs();

        // Auto-poll if any job is running or queued
        const hasActive = allJobs.some(j => j.status === "running" || j.status === "queued");
        if (hasActive) {
            startPolling();
        } else {
            stopPolling();
        }
    } catch (e) {
        console.error("Failed to load jobs:", e);
    }
}

function renderJobs() {
    const filter = document.getElementById("job-filter").value;
    const list = document.getElementById("all-jobs");
    const filtered = filter === "all" ? allJobs : allJobs.filter(j => j.status === filter);

    if (filtered.length === 0) {
        list.innerHTML = '<li style="color:var(--text-muted);padding:0.5rem;">No jobs</li>';
        return;
    }

    list.innerHTML = filtered.map(j => jobItemHTML(j, true)).join("");
}

function renderRecentJobs() {
    const list = document.getElementById("recent-jobs");
    const recent = allJobs.slice(0, 5);

    if (recent.length === 0) {
        list.innerHTML = '<li style="color:var(--text-muted);padding:0.5rem;">No jobs yet</li>';
        return;
    }

    list.innerHTML = recent.map(j => jobItemHTML(j, false)).join("");
}

function jobItemHTML(job, showDetails) {
    const p = job.progress || {};
    const total = (p.total_discovered || 0);
    const done = (p.total_uploaded || 0) + (p.total_skipped || 0) + (p.total_duplicates || 0) + (p.total_errors || 0);
    const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
    const fillClass = job.status === "completed" ? "done" : (job.status === "failed" ? "error" : "");

    let details = "";
    if (showDetails) {
        details = `
            <div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem;">
                Discovered: ${p.total_discovered || 0} |
                Uploaded: ${p.total_uploaded || 0} |
                Dupes: ${p.total_duplicates || 0} |
                Errors: ${p.total_errors || 0}
            </div>`;

        if (p.errors && p.errors.length > 0) {
            details += `<ul class="error-list">${p.errors.map(e => `<li>${escHTML(e)}</li>`).join("")}</ul>`;
        }
    }

    const cancelBtn = (job.status === "running" || job.status === "queued")
        ? `<button class="btn btn-danger btn-sm" onclick="cancelJob('${job.job_id}')">Cancel</button>`
        : "";

    return `
        <li class="job-item" style="flex-direction:column;align-items:stretch;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div class="job-info">
                    <div class="job-url">${escHTML(job.urls.join(", "))}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);">${job.created_at || ""}</div>
                </div>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    <span class="job-status ${job.status}">${job.status}</span>
                    ${cancelBtn}
                </div>
            </div>
            <div class="progress-bar"><div class="progress-fill ${fillClass}" style="width:${pct}%"></div></div>
            ${details}
        </li>`;
}

async function cancelJob(jobId) {
    try {
        await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
        toast("Job cancelled", "info");
        loadJobs();
    } catch (e) {
        toast("Failed to cancel job", "error");
    }
}

// --- Polling ---
function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(() => {
        loadJobs();
    }, 3000);
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

// --- Settings ---
async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        currentSettings = await res.json();
        populateSettings(currentSettings);
    } catch (e) {
        console.error("Failed to load settings:", e);
    }
}

function populateSettings(s) {
    const r = s.resolution || {};
    const sc = s.scraper || {};
    const c = s.compression || {};
    const d = s.deduplication || {};

    document.getElementById("set-min-width").value = r.min_width || 1920;
    document.getElementById("set-min-height").value = r.min_height || 1080;
    document.getElementById("set-delay").value = sc.request_delay_seconds || 2;
    document.getElementById("set-max-pages").value = sc.max_pages_per_site || 50;
    document.getElementById("set-concurrent").value = sc.max_concurrent_downloads || 3;
    document.getElementById("set-timeout").value = sc.page_load_timeout_seconds || 30;
    document.getElementById("set-quality").value = c.quality || 85;
    document.getElementById("quality-val").textContent = c.quality || 85;
    document.getElementById("set-dedup-enabled").checked = d.enabled !== false;
    document.getElementById("set-hamming").value = d.hamming_distance_threshold || 8;
    document.getElementById("set-check-baserow").checked = d.check_baserow !== false;

    // Aspect ratio checkboxes in settings
    const container = document.getElementById("settings-ratios");
    const allRatios = ["16:9", "9:16", "21:9", "4:3", "3:2", "1:1", "32:9"];
    const enabled = r.target_aspect_ratios || allRatios;
    container.innerHTML = allRatios.map(ratio => {
        const checked = enabled.includes(ratio) ? "checked" : "";
        return `<label><input type="checkbox" value="${ratio}" ${checked}> ${ratio}</label>`;
    }).join("");
}

async function saveSettings() {
    const ratios = [];
    document.querySelectorAll("#settings-ratios input:checked").forEach(cb => ratios.push(cb.value));

    const body = {
        resolution: {
            min_width: parseInt(document.getElementById("set-min-width").value) || 1920,
            min_height: parseInt(document.getElementById("set-min-height").value) || 1080,
            target_aspect_ratios: ratios,
        },
        scraper: {
            request_delay_seconds: parseFloat(document.getElementById("set-delay").value) || 2,
            max_pages_per_site: parseInt(document.getElementById("set-max-pages").value) || 50,
            max_concurrent_downloads: parseInt(document.getElementById("set-concurrent").value) || 3,
            page_load_timeout_seconds: parseInt(document.getElementById("set-timeout").value) || 30,
        },
        compression: {
            quality: parseInt(document.getElementById("set-quality").value) || 85,
        },
        deduplication: {
            enabled: document.getElementById("set-dedup-enabled").checked,
            hamming_distance_threshold: parseInt(document.getElementById("set-hamming").value) || 8,
            check_baserow: document.getElementById("set-check-baserow").checked,
        },
    };

    try {
        const res = await fetch("/api/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (res.ok) {
            toast("Settings saved", "success");
            const saved = document.getElementById("settings-saved");
            saved.textContent = "Last saved: " + new Date().toLocaleTimeString();
            saved.style.display = "inline";
        } else {
            toast("Failed to save settings", "error");
        }
    } catch (e) {
        toast("Network error", "error");
    }
}

// --- Baserow ---
async function loadBaserowConfig() {
    try {
        const res = await fetch("/api/settings");
        const data = await res.json();
        const br = data.baserow || {};
        document.getElementById("br-url").value = br.api_url || "";
        document.getElementById("br-table").value = br.table_id || 810;
        // Token is masked in API response — don't overwrite if masked
        if (br.api_token && !br.api_token.startsWith("***")) {
            document.getElementById("br-token").value = br.api_token;
        }
    } catch (e) {
        console.error("Failed to load Baserow config:", e);
    }
}

async function testBaserow() {
    const statusEl = document.getElementById("br-status");
    statusEl.innerHTML = '<span class="spinner"></span> Testing connection...';

    // Save first so test uses latest values
    await saveBaserowSilent();

    try {
        const res = await fetch("/api/baserow/test", { method: "POST" });
        const data = await res.json();

        if (data.success) {
            statusEl.innerHTML = `<span style="color:var(--success);">Connected! Table has ${data.row_count} rows.</span>`;
        } else {
            statusEl.innerHTML = `<span style="color:var(--error);">Failed: ${escHTML(data.error || "Unknown error")}</span>`;
        }
    } catch (e) {
        statusEl.innerHTML = `<span style="color:var(--error);">Network error: ${escHTML(e.message)}</span>`;
    }
}

async function saveBaserowSilent() {
    const url = document.getElementById("br-url").value.trim();
    const token = document.getElementById("br-token").value.trim();
    const tableId = parseInt(document.getElementById("br-table").value) || 810;

    await fetch("/api/baserow/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_url: url, api_token: token, table_id: tableId }),
    });
}

async function saveBaserow() {
    await saveBaserowSilent();
    toast("Baserow config saved", "success");
    loadHealth(); // Refresh header status
}

function togglePassword() {
    const input = document.getElementById("br-token");
    const btn = input.nextElementSibling;
    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "Hide";
    } else {
        input.type = "password";
        btn.textContent = "Show";
    }
}

// --- Stats ---
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();

        document.getElementById("stat-scraped").textContent = data.total_scraped || 0;
        document.getElementById("stat-uploaded").textContent = data.total_uploaded || 0;
        document.getElementById("stat-dupes").textContent = data.total_duplicates || 0;
        document.getElementById("stat-errors").textContent = data.total_errors || 0;

        // Aspect ratio chart
        renderBarChart("ratio-chart", data.aspect_ratio_breakdown || {});

        // Site chart
        renderBarChart("site-chart", data.site_breakdown || {});

        // System info
        const info = document.getElementById("sys-info");
        const uptime = data.uptime_seconds ? formatUptime(data.uptime_seconds) : "N/A";
        info.innerHTML = `
            <div>AI Model: ${escHTML(data.ai_model || "N/A")}</div>
            <div>Browser: ${escHTML(data.browser_status || "N/A")}</div>
            <div>Uptime: ${uptime}</div>
        `;
    } catch (e) {
        console.error("Failed to load stats:", e);
    }
}

function renderBarChart(containerId, data) {
    const container = document.getElementById(containerId);
    const entries = Object.entries(data);

    if (entries.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);font-size:0.85rem;">No data yet</div>';
        return;
    }

    const maxVal = Math.max(...entries.map(e => e[1]), 1);

    container.innerHTML = entries.map(([label, count]) => {
        const pct = Math.round((count / maxVal) * 100);
        return `
            <div class="bar-row">
                <div class="bar-label">${escHTML(label)}</div>
                <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
                <div class="bar-count">${count}</div>
            </div>`;
    }).join("");
}

// --- Toast ---
function toast(message, type = "info") {
    const container = document.getElementById("toasts");
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => {
        el.style.opacity = "0";
        el.style.transition = "opacity 0.3s";
        setTimeout(() => el.remove(), 300);
    }, 4000);
}

// --- Helpers ---
function escHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function formatUptime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}
