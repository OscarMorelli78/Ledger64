"use strict";
// No network request before the visitor explicitly submits the form.
const form = document.getElementById("commercial");
const allowed = new Set(["Installation","Support","Integration","Custom development","Training","Other"]);
const scopes = new Set(["Exploratory enquiry","Single deployment","Multiple deployments"]);
form.addEventListener("submit", event => {
  event.preventDefault();
  const service = document.getElementById("service").value;
  const scope = document.getElementById("scale").value;
  if (!document.getElementById("consent").checked || !allowed.has(service) || !scopes.has(scope)) return;
  const url = new URL("https://github.com/OscarMorelli78/Ledger64/issues/new");
  url.searchParams.set("title", "[Commercial] " + service);
  url.searchParams.set("template", "commercial.yml");
  url.searchParams.set("objective", "Service: " + service + "\nScope: " + scope + "\nPlease advise on next steps and a private contact channel if necessary.\nNo confidential information included.");
  window.location.assign(url.toString());
});
