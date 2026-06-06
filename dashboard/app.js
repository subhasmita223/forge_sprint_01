/* app.js — SEO Command Center live cockpit. Plain DOM + SSE, no build step. */
const $ = (id) => document.getElementById(id);
let totals = { High: 0, Medium: 0, Low: 0, total: 0 };

function log(msg) {
  const l = $("log"); if (l.querySelector(".empty")) l.innerHTML = "";
  const d = document.createElement("div"); d.textContent = "› " + msg; l.appendChild(d); l.scrollTop = l.scrollHeight;
}
function addIssue(i) {
  const tb = $("tbody"); if (tb.querySelector(".empty")) tb.innerHTML = "";
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><span class="sev ${i.severity.toLowerCase()}">${i.severity}</span></td>
                  <td>${i.type}</td><td>${i.count}</td>`;
  tb.appendChild(tr);
  totals[i.severity] = (totals[i.severity] || 0) + 1; totals.total++;
  $("c-total").textContent = totals.total; $("c-high").textContent = totals.High;
  $("c-med").textContent = totals.Medium; $("c-low").textContent = totals.Low;
}
function showDeliverable() {
  $("export").innerHTML = "<b>report.html written ✓</b><br><span style='color:#c8c5be;font-size:12px'>Open or email outputs/report.html to the client.</span>";
}
function handle({ event, data }) {
  if (event === "snapshot") {
    // Sent once on connect. Reconstruct ALL three panels from persisted RUN state so a
    // dashboard opened/refreshed AFTER the run finished isn't stuck on placeholder text
    // (the live events that normally fill the Run log + Deliverable already fired).
    totals = { High: 0, Medium: 0, Low: 0, total: 0 };
    $("tbody").innerHTML = '<tr><td colspan="3" class="empty">Waiting for the audit to run…</td></tr>';
    $("log").innerHTML = '<div class="empty">Pipeline steps stream here.</div>';
    if (data.site) { $("meta").textContent = "· " + data.site; $("urls").textContent = (data.urls||0) + " URLs"; }
    // Issues table
    (data.issues || []).forEach(addIssue);
    // Run log — replay the steps the live events would have logged
    if (data.urls) log(`Loaded ${data.urls} URLs from ${data.site}`);
    (data.issues || []).forEach((i) => log(`Found ${i.count} × ${i.type}`));
    if (data.summary) log(`Audit complete: ${data.summary.total_issues} issue types`);
    if (data.fixes) log(`Fixes ready: ${(data.fixes.titles||[]).length} titles, ${(data.fixes.redirect_map||[]).length} redirects`);
    if ((data.recommendations || []).length) log(`${data.recommendations.length} recommendations ready`);
    if (data.report_json) log("report.json saved");
    // Deliverable
    if (data.report_html) showDeliverable();
  } else if (event === "loaded") {
    $("meta").textContent = "· " + data.site; $("urls").textContent = data.urls + " URLs";
    log(`Loaded ${data.urls} URLs from ${data.site}`); $("tbody").innerHTML = "";
    totals = { High:0, Medium:0, Low:0, total:0 };
  } else if (event === "issue") { addIssue(data); log(`Found ${data.count} × ${data.type}`); }
  else if (event === "summary") { log(`Audit complete: ${data.total_issues} issue types`); }
  else if (event === "fixes") { log(`Fixes ready: ${(data.titles||[]).length} titles, ${(data.redirect_map||[]).length} redirects`); }
  else if (event === "recommendations") { log(`${(data.recommendations||[]).length} recommendations ready`); }
  else if (event === "exported") { showDeliverable(); }
  else if (event === "saved") { log("report.json saved"); }
}
const es = new EventSource("/events");
es.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (e) {} };
