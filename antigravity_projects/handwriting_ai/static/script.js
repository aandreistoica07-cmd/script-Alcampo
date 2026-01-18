const drawCanvas = document.getElementById('drawCanvas');
const drawCtx = drawCanvas.getContext('2d');
const smallCanvas = document.getElementById('smallCanvas');
const smallCtx = smallCanvas.getContext('2d');

// Drawing state
let isDrawing = false;
let lastX = 0;
let lastY = 0;

// Setup Drawing
drawCtx.strokeStyle = 'white';
drawCtx.lineWidth = 15;
drawCtx.lineCap = 'round';
drawCtx.fillStyle = 'black';
drawCtx.fillRect(0, 0, drawCanvas.width, drawCanvas.height);

drawCanvas.addEventListener('mousedown', (e) => {
    isDrawing = true;
    [lastX, lastY] = [e.offsetX, e.offsetY];
});

drawCanvas.addEventListener('mousemove', (e) => {
    if (!isDrawing) return;
    draw(e.offsetX, e.offsetY);
});

drawCanvas.addEventListener('mouseup', () => isDrawing = false);
drawCanvas.addEventListener('mouseout', () => isDrawing = false);

function draw(x, y) {
    drawCtx.beginPath();
    drawCtx.moveTo(lastX, lastY);
    drawCtx.lineTo(x, y);
    drawCtx.stroke();
    [lastX, lastY] = [x, y];
    updateSmallCanvas();
}

function updateSmallCanvas() {
    // Downscale to 28x28
    smallCtx.drawImage(drawCanvas, 0, 0, 28, 28);
    // Auto predict on draw? maybe better to have explicit button or throttle
}

document.getElementById('clearBtn').addEventListener('click', () => {
    drawCtx.fillStyle = 'black';
    drawCtx.fillRect(0, 0, drawCanvas.width, drawCanvas.height);
    updateSmallCanvas();
    resetBars();
});

// Charts
const lossCtx = document.getElementById('lossChart').getContext('2d');
const accCtx = document.getElementById('accChart').getContext('2d');

const lossChart = new Chart(lossCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Loss',
            data: [],
            borderColor: '#ef4444',
            tension: 0.1
        }]
    },
    options: {
        animation: false,
        responsive: true,
        scales: { x: { display: false } }
    }
});

const accChart = new Chart(accCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Accuracy',
            data: [],
            borderColor: '#3b82f6',
            tension: 0.1
        }]
    },
    options: {
        animation: false,
        responsive: true,
        scales: {
            x: { display: false },
            y: { min: 0, max: 1 }
        }
    }
});

// Training Logic
let isTraining = false;
const trainBtn = document.getElementById('trainBtn');

trainBtn.addEventListener('click', () => {
    isTraining = !isTraining;
    trainBtn.innerText = isTraining ? 'Stop Training' : 'Start Training';
    trainBtn.classList.toggle('danger');
    if (isTraining) trainLoop();
});

async function trainLoop() {
    let step = 0;
    while (isTraining) {
        try {
            const res = await fetch('/train_step', { method: 'POST' });
            const data = await res.json();

            // Update charts
            const time = new Date().toLocaleTimeString();
            lossChart.data.labels.push(time);
            lossChart.data.datasets[0].data.push(data.loss);
            accChart.data.labels.push(time);
            accChart.data.datasets[0].data.push(data.accuracy);

            if (lossChart.data.labels.length > 50) {
                lossChart.data.labels.shift();
                lossChart.data.datasets[0].data.shift();
                accChart.data.labels.shift();
                accChart.data.datasets[0].data.shift();
            }

            lossChart.update();
            accChart.update();
        } catch (e) {
            console.error(e);
            isTraining = false;
        }
        // Small delay to not kill browser
        await new Promise(r => setTimeout(r, 100));
    }
}

// Prediction
document.getElementById('predictBtn').addEventListener('click', predict);

async function predict() {
    // Get pixel data from small canvas
    const imageData = smallCtx.getImageData(0, 0, 28, 28);
    // Convert to grayscale 2D array
    const pixels = [];
    for (let i = 0; i < 28; i++) {
        const row = [];
        for (let j = 0; j < 28; j++) {
            // RGBA, just take R or average. In b&w drawing R=G=B.
            // But wait, black background = 0, white stroke = 255.
            const idx = (i * 28 + j) * 4;
            row.push(imageData.data[idx]);
        }
        pixels.push(row);
    }

    const res = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: pixels })
    });
    const data = await res.json();
    updateBars(data.probabilities);
    updateNetViz(data.hidden_activations, data.probabilities);

    // Draw centered input to small canvas for debugging user view
    const centered = data.input_centered;
    const idata = smallCtx.createImageData(28, 28);
    for (let i = 0; i < 28; i++) {
        for (let j = 0; j < 28; j++) {
            const val = centered[i][j] * 255;
            const idx = (i * 28 + j) * 4;
            idata.data[idx] = val; // R
            idata.data[idx + 1] = val; // G
            idata.data[idx + 2] = val; // B
            idata.data[idx + 3] = 255; // A
        }
    }
    smallCtx.putImageData(idata, 0, 0);
}

const netCanvas = document.getElementById('netCanvas');
const netCtx = netCanvas.getContext('2d');

function updateNetViz(hidden, output) {
    const w = netCanvas.width;
    const h = netCanvas.height;
    netCtx.clearRect(0, 0, w, h);

    // Draw Hidden Layer (Sample of neurons)
    const hCols = 16;
    const hRows = 16;
    const cellW = 10;
    const cellH = 10;
    const startX = 50;
    const startY = (h - (hRows * cellH)) / 2;

    netCtx.fillStyle = '#94a3b8';
    netCtx.font = "12px Inter";
    netCtx.fillText("Hidden Layer Activations", startX, startY - 10);

    hidden.forEach((val, idx) => {
        const r = Math.floor(idx / hCols);
        const c = idx % hCols;
        const x = startX + c * cellW;
        const y = startY + r * cellH;

        const alpha = Math.min(1, Math.max(0, val)); // ReLU range
        netCtx.fillStyle = `rgba(59, 130, 246, ${alpha})`;
        netCtx.fillRect(x, y, cellW - 1, cellH - 1);
    });

    // Draw Output Layer
    const outX = 300;
    const outSpacing = 25;
    const outYStart = (h - (10 * outSpacing)) / 2;

    netCtx.fillStyle = '#94a3b8';
    netCtx.fillText("Output", outX, outYStart - 10);

    output.forEach((val, idx) => {
        const y = outYStart + idx * outSpacing;

        // Line from hidden block to output (symbolic)
        netCtx.beginPath();
        netCtx.moveTo(startX + hCols * cellW + 10, h / 2);
        netCtx.lineTo(outX, y + 5);
        netCtx.strokeStyle = `rgba(255,255,255, ${val * 0.5})`;
        netCtx.stroke();

        // Node
        netCtx.beginPath();
        netCtx.arc(outX, y + 5, 8, 0, Math.PI * 2);
        netCtx.fillStyle = `rgba(59, 130, 246, ${val})`;
        netCtx.fill();
        netCtx.strokeStyle = '#fff';
        netCtx.stroke();

        // Label
        netCtx.fillStyle = '#fff';
        netCtx.fillText(idx, outX + 15, y + 9);
    });
}

function updateBars(probs) {
    const barsContainer = document.getElementById('bars');
    barsContainer.innerHTML = '';
    probs.forEach((p, i) => {
        const percent = (p * 100).toFixed(1);
        const row = document.createElement('div');
        row.className = 'bar-row';
        row.innerHTML = `
            <span class="bar-label">${i}</span>
            <div class="bar-bg">
                <div class="bar-fill" style="width: ${percent}%"></div>
            </div>
            <span class="bar-percent">${percent}%</span>
        `;
        barsContainer.appendChild(row);
    });
}

function resetBars() {
    document.getElementById('bars').innerHTML = '';
}

document.getElementById('resetBtn').addEventListener('click', async () => {
    await fetch('/reset', { method: 'POST' });
    lossChart.data.labels = [];
    lossChart.data.datasets[0].data = [];
    accChart.data.labels = [];
    accChart.data.datasets[0].data = [];
    lossChart.update();
    accChart.update();
});
