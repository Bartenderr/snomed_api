// Handle tab switching
function switchTab(tabId) {
  // Hide all tab contents
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // Deactivate all tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Show the selected tab content
  document.getElementById(tabId).classList.add('active');
  
  // Activate the clicked tab button
  event.target.classList.add('active');
}

// Handle text-based tariff submission
async function submitTariffs() {
  const input = document.getElementById("tariffInput").value;
  const names = input.split("\n").map(x => x.trim()).filter(Boolean);

  if (names.length === 0) {
    alert("Please enter at least one tariff name.");
    return;
  }

  const response = await fetch("/api/v1/match", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ tariff_names: names })
  });

  if (!response.ok) {
    alert("Something went wrong. Please check your API connection.");
    return;
  }

  const data = await response.json();
  const results = data.results;

  const tbody = document.getElementById("resultsBody");
  tbody.innerHTML = "";

  results.forEach(r => {
    const score = (r.similarity_score * 100);
    const scoreFormatted = score.toFixed(2) + "%";
    const scoreClass = score >= 70 ? "highlight-green" : "";

    const row = `<tr>
      <td>${r.input_name}</td>
      <td>${r.matched_name}</td>
      <td>${r.snomed_code}</td>
      <td>${r.snomed_description}</td>
      <td class="${scoreClass}">${scoreFormatted}</td>
    </tr>`;
    tbody.innerHTML += row;
  });

  document.getElementById("resultsSection").classList.remove("hidden");
}

// Update filename display when a file is selected
document.addEventListener('DOMContentLoaded', function() {
  const fileInput = document.getElementById('tariffFile');
  if (fileInput) {
    fileInput.addEventListener('change', function() {
      const fileName = fileInput.files[0] ? fileInput.files[0].name : 'No file chosen';
      document.getElementById('fileName').textContent = fileName;
    });
  }
});

// Handle Excel file upload
async function uploadTariffFile() {
  const fileInput = document.getElementById("tariffFile");
  
  if (!fileInput.files || fileInput.files.length === 0) {
    alert("Please select an Excel file.");
    return;
  }
  
  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);
  
  // Show progress indicator
  document.getElementById("uploadProgress").classList.remove("hidden");
  document.getElementById("fileResultsSection").classList.add("hidden");
  
  try {
    const response = await fetch("/api/v1/process-excel", {
      method: "POST",
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "An error occurred while processing the file");
    }
    
    const result = await response.json();
    
    // Update progress to 100%
    document.querySelector('.progress-fill').style.width = '100%';
    document.getElementById('progressStatus').textContent = 'Processing complete!';
    
    // Display stats
    document.getElementById("processingStats").innerHTML = `
      <p>Total tariff items processed: <strong>${result.total_rows}</strong></p>
      <p>Duplicate items found: <strong>${result.duplicated_rows}</strong></p>
    `;
    
    // Setup download button
    const downloadButton = document.getElementById("downloadButton");
    downloadButton.onclick = () => {
      window.location.href = `/api/v1/download/${result.file_id}`;
    };
    
    // Show results section
    document.getElementById("fileResultsSection").classList.remove("hidden");
  } catch (error) {
    alert(error.message || "An error occurred while processing the file");
  } finally {
    // Hide progress after a short delay
    setTimeout(() => {
      document.getElementById("uploadProgress").classList.add("hidden");
      document.querySelector('.progress-fill').style.width = '0%';
    }, 1000);
  }
}