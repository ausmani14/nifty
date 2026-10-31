// NIFTY AI Professional Dashboard Client-side JavaScript
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  loadAllDashboardData();
});

// Setup tab navigation
function setupTabs() {
  const navButtons = document.querySelectorAll('.nav-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      navButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(pane => pane.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });
}

// Data paths: try local data/ first, then relative website_data/
async function fetchJSON(filename) {
  const candidatePaths = [
    `data/${filename}`,
    `./data/${filename}`,
    `../website_data/${filename}`,
    `website_data/${filename}`,
    `./website_data/${filename}`
  ];

  for (const path of candidatePaths) {
    try {
      const resp = await fetch(path);
      if (resp.ok) {
        return await resp.json();
      }
    } catch (e) {
      // try next path
    }
  }
  return null;
}

// Format UTC timestamp to Asia/Kolkata (IST)
function formatIST(isoUtcString) {
  if (!isoUtcString || isoUtcString === '--') return '--';
  try {
    const d = new Date(isoUtcString);
    if (isNaN(d.getTime())) return isoUtcString;
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }) + ' IST';
  } catch (e) {
    return isoUtcString;
  }
}

async function loadAllDashboardData() {
  const [latestPred, sysStatus, modelInfo, predHist, outHist, perfSummary] = await Promise.all([
    fetchJSON('latest_prediction.json'),
    fetchJSON('system_status.json'),
    fetchJSON('model_info.json'),
    fetchJSON('prediction_history.json'),
    fetchJSON('outcome_history.json'),
    fetchJSON('performance_summary.json')
  ]);

  renderLatestPrediction(latestPred);
  renderSystemStatus(sysStatus);
  renderModelInfo(modelInfo);
  renderHistory(predHist, outHist);
  renderAnalytics(perfSummary);
}

function renderLatestPrediction(data) {
  if (!data) return;

  const badge = document.getElementById('overview-badge');
  const predVal = document.getElementById('overview-pred-val');
  const predBps = document.getElementById('overview-pred-bps');
  const targetDate = document.getElementById('overview-target-date');
  const outcomeVal = document.getElementById('overview-outcome-val');
  const outcomeStatus = document.getElementById('overview-outcome-status');

  // Daily tab elements
  const dailyReturn = document.getElementById('daily-pred-return');
  const dailyBps = document.getElementById('daily-pred-bps');
  const dailyDir = document.getElementById('daily-dir-bias');
  const dailyTarget = document.getElementById('daily-target-date');
  const dailyGenAt = document.getElementById('daily-generated-at');
  const dailyPredId = document.getElementById('daily-pred-id');
  const dailyValStatus = document.getElementById('daily-val-status');
  const dailyOutStatus = document.getElementById('daily-out-status');

  const status = data.prediction_status || 'NO VALID PROSPECTIVE PREDICTION';
  badge.textContent = status;
  badge.className = 'status-badge ' + (
    status === 'VALID' ? 'badge-valid' :
    (status.includes('PENDING') ? 'badge-pending' :
    (status.includes('BLOCKED') || status.includes('FAILURE') ? 'badge-blocked' : 'badge-neutral'))
  );

  if (data.has_prediction) {
    const retVal = data.expected_return;
    const bpsVal = data.expected_return_bps;
    const signStr = retVal > 0 ? '+' : '';

    predVal.textContent = `${signStr}${(retVal * 100).toFixed(2)}%`;
    predVal.className = 'card-value ' + (retVal > 0 ? 'val-positive' : (retVal < 0 ? 'val-negative' : 'val-neutral'));
    predBps.textContent = `${signStr}${bpsVal.toFixed(1)} bps (${data.directional_bias})`;

    dailyReturn.textContent = `${signStr}${(retVal * 100).toFixed(4)}%`;
    dailyBps.textContent = `${signStr}${bpsVal.toFixed(2)} bps`;
    dailyDir.textContent = data.directional_bias;

    targetDate.textContent = data.target_date || '--';
    dailyTarget.textContent = data.target_date || '--';
    dailyGenAt.textContent = formatIST(data.last_updated_utc);
    dailyPredId.textContent = data.prediction_id || '--';
    dailyValStatus.textContent = 'PASSED (08:50 IST Cutoff)';
    dailyOutStatus.textContent = data.outcome_status || 'PENDING';

    if (data.realized_outcome) {
      const outRet = data.realized_outcome.realized_t0;
      const outSign = outRet > 0 ? '+' : '';
      outcomeVal.textContent = `${outSign}${(outRet * 100).toFixed(2)}%`;
      outcomeVal.className = 'card-value ' + (outRet > 0 ? 'val-positive' : (outRet < 0 ? 'val-negative' : 'val-neutral'));
      outcomeStatus.textContent = `Error: ${data.realized_outcome.absolute_error_bps.toFixed(1)} bps | Match: ${data.realized_outcome.directional_match ? 'YES' : 'NO'}`;
    } else {
      outcomeVal.textContent = 'PENDING';
      outcomeStatus.textContent = 'Awaiting 15:30 IST Cash Market Close';
    }
  } else {
    predVal.textContent = '--';
    predBps.textContent = data.message || 'No prospective predictions recorded yet.';
    targetDate.textContent = data.target_date || 'Next Session';
    outcomeVal.textContent = '--';
    outcomeStatus.textContent = 'Status: N/A';

    dailyReturn.textContent = '--';
    dailyBps.textContent = '--';
    dailyDir.textContent = 'NEUTRAL';
    dailyTarget.textContent = 'Next Session';
    dailyGenAt.textContent = formatIST(data.last_updated_utc);
    dailyPredId.textContent = 'None';
    dailyValStatus.textContent = status;
    dailyOutStatus.textContent = 'N/A';
  }
}

function renderSystemStatus(data) {
  if (!data) return;

  const modelHash = document.getElementById('overview-model-hash');
  const tipHash = document.getElementById('overview-tip-hash');
  const predCount = document.getElementById('overview-pred-count');
  const outCount = document.getElementById('overview-out-count');
  const stateEl = document.getElementById('status-system-state');
  const lastUpdated = document.getElementById('status-last-updated');
  const statusTip = document.getElementById('status-tip-hash');
  const chainValid = document.getElementById('status-chain-valid');

  if (modelHash && data.model_integrity) {
    modelHash.textContent = (data.model_integrity.model_sha256 || '').substring(0, 16) + '...';
  }
  if (tipHash && data.ledger_integrity) {
    tipHash.textContent = (data.ledger_integrity.tip_hash || '').substring(0, 16) + '...';
    if (statusTip) statusTip.textContent = (data.ledger_integrity.tip_hash || '').substring(0, 16) + '...';
    if (predCount) predCount.textContent = data.ledger_integrity.prediction_count || 0;
    if (outCount) outCount.textContent = data.ledger_integrity.outcome_count || 0;
  }
  if (stateEl) stateEl.textContent = data.current_system_state || '--';
  if (lastUpdated) lastUpdated.textContent = formatIST(data.last_updated_utc);
  if (chainValid && data.ledger_integrity) {
    chainValid.textContent = data.ledger_integrity.is_valid ? 'INTACT' : 'CORRUPTED';
    chainValid.className = 'status-badge ' + (data.ledger_integrity.is_valid ? 'badge-valid' : 'badge-blocked');
  }
}

function renderModelInfo(data) {
  // Model research tab static text is already in index.html; can update dynamic fields if any
}

function renderHistory(predData, outData) {
  const historyBody = document.getElementById('history-table-body');
  const actualBody = document.getElementById('actual-table-body');

  const preds = predData && predData.predictions ? predData.predictions : [];
  const outs = outData && outData.outcomes ? outData.outcomes : [];
  const outMap = {};
  outs.forEach(o => { outMap[o.prediction_id] = o; });

  // 1. Predictions Table
  if (historyBody) {
    if (preds.length === 0) {
      historyBody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">No prospective predictions recorded yet. Ledger is in genesis state.</td></tr>';
    } else {
      historyBody.innerHTML = preds.map(p => {
        const retSign = p.predicted_return > 0 ? '+' : '';
        const isRec = p.prediction_id in outMap;
        return `
          <tr>
            <td>${p.session_date}</td>
            <td>${p.target_date}</td>
            <td class="${p.predicted_return > 0 ? 'val-positive' : (p.predicted_return < 0 ? 'val-negative' : 'val-neutral')}">${retSign}${(p.predicted_return * 100).toFixed(2)}%</td>
            <td>${retSign}${p.predicted_return_bps.toFixed(1)}</td>
            <td>${p.predicted_return > 0 ? 'POSITIVE' : 'NEGATIVE'}</td>
            <td><span class="status-badge ${isRec ? 'badge-valid' : 'badge-pending'}">${isRec ? 'RECONCILED' : 'PENDING'}</span></td>
            <td><code>${(p.record_hash || '').substring(0, 12)}...</code></td>
          </tr>
        `;
      }).join('');
    }
  }

  // 2. Actual vs Predicted Table
  if (actualBody) {
    if (outs.length === 0) {
      actualBody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">No reconciled session pairs available yet.</td></tr>';
    } else {
      actualBody.innerHTML = outs.map(o => {
        const pred = preds.find(p => p.prediction_id === o.prediction_id);
        const predBps = pred ? pred.predicted_return_bps.toFixed(1) : '--';
        const actualSign = o.realized_t0 > 0 ? '+' : '';
        return `
          <tr>
            <td>${o.session_date}</td>
            <td>${predBps}</td>
            <td>${o.realized_open.toFixed(2)}</td>
            <td>${o.realized_close.toFixed(2)}</td>
            <td class="${o.realized_t0 > 0 ? 'val-positive' : (o.realized_t0 < 0 ? 'val-negative' : 'val-neutral')}">${actualSign}${o.realized_t0_bps.toFixed(1)}</td>
            <td>${o.absolute_error_bps.toFixed(1)}</td>
            <td><span class="status-badge ${o.directional_match ? 'badge-valid' : 'badge-blocked'}">${o.directional_match ? 'MATCH' : 'MISMATCH'}</span></td>
          </tr>
        `;
      }).join('');
    }
  }
}

function renderAnalytics(perfData) {
  if (!perfData) return;
  const metrics = perfData.prospective_metrics;
  const nEl = document.getElementById('analytics-n');
  const icEl = document.getElementById('analytics-ic');
  const maeEl = document.getElementById('analytics-mae');
  const mdaEl = document.getElementById('analytics-mda');

  if (metrics && metrics.sample_size > 0) {
    if (nEl) nEl.textContent = metrics.sample_size;
    if (icEl) icEl.textContent = metrics.pearson_ic !== undefined ? metrics.pearson_ic.toFixed(4) : 'N/A';
    if (maeEl) maeEl.textContent = metrics.model_mae_bps !== undefined ? `${metrics.model_mae_bps.toFixed(2)} bps` : 'N/A';
    if (mdaEl) mdaEl.textContent = metrics.model_mda_pct !== undefined ? `${metrics.model_mda_pct.toFixed(1)}%` : 'N/A';
  } else {
    if (nEl) nEl.textContent = '0';
    if (icEl) icEl.textContent = 'N/A';
    if (maeEl) maeEl.textContent = 'N/A';
    if (mdaEl) mdaEl.textContent = 'N/A';
  }
}
