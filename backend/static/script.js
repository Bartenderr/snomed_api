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
