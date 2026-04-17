const latInput = document.getElementById('lat');
const lonInput = document.getElementById('lon');
const radiusInput = document.getElementById('radius');
const questionInput = document.getElementById('question');
const askButton = document.getElementById('ask');
const locateButton = document.getElementById('locate');
const replyBox = document.getElementById('reply');
const rowsBody = document.getElementById('rows');

locateButton.addEventListener('click', () => {
  if (!navigator.geolocation) {
    replyBox.textContent = 'Geolocation is not available in this browser.';
    return;
  }
  navigator.geolocation.getCurrentPosition((position) => {
    latInput.value = position.coords.latitude;
    lonInput.value = position.coords.longitude;
  }, (error) => {
    replyBox.textContent = `Location failed: ${error.message}`;
  });
});

askButton.addEventListener('click', async () => {
  const payload = {
    question: questionInput.value,
    lat: Number(latInput.value),
    lon: Number(lonInput.value),
    radius_km: Number(radiusInput.value || 10),
  };

  if (!payload.question || Number.isNaN(payload.lat) || Number.isNaN(payload.lon)) {
    replyBox.textContent = 'Please provide a question and valid location.';
    return;
  }

  rowsBody.innerHTML = '';
  replyBox.textContent = 'Thinking...';

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      replyBox.textContent = data.error || 'Request failed';
      return;
    }

    replyBox.textContent = data.reply;

    for (const item of data.results) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${item.station}</td>
        <td>${item.fuel_type}</td>
        <td>${item.price.toFixed(3)}</td>
        <td>${item.fetched_at}</td>
      `;
      rowsBody.appendChild(tr);
    }
  } catch (err) {
    replyBox.textContent = `Error: ${err.message}`;
  }
});
