  // Automation form handling
  document.getElementById('automationForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const topicInput = document.getElementById('topicInput');
    const scheduleTimeInput = document.getElementById('scheduleDateTime');
    const timezoneSelect = document.getElementById('scheduleTimezone');
    const platformCheckboxes = document.querySelectorAll('input[name="platforms"]:checked');
    const resultDiv = document.getElementById('automationResult');
    
    const topic = topicInput.value.trim();
    const scheduleTime = scheduleTimeInput.value;
    const timezone = timezoneSelect.value;
    
    if (!topic || !scheduleTime) {
      resultDiv.innerHTML = '<div style="color: red;">❌ Please fill in all required fields.</div>';
      return;
    }
    
    if (platformCheckboxes.length === 0) {
      resultDiv.innerHTML = '<div style="color: red;">❌ Please select at least one social media platform.</div>';
      return;
    }
    
    // Get selected platforms
    const selectedPlatforms = Array.from(platformCheckboxes).map(cb => cb.value);
    
    // Disable submit button during request
    const submitButton = event.submitter;
    submitButton.disabled = true;
    submitButton.textContent = "Scheduling...";
    
    try {
      const response = await fetch('/schedule-automation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          topic: topic,
          schedule_time: scheduleTime,
          timezone: timezone,
          platforms: selectedPlatforms
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        resultDiv.innerHTML = '<div style="color: green;">✅ Automation scheduled successfully!</div>';
        // Reset the form after successful submission
        setTimeout(() => {
          document.getElementById('automationForm').reset();
        }, 2000);
      } else {
        resultDiv.innerHTML = `<div style="color: red;">❌ Error: ${result.error || 'Schedule failed'}</div>`;
      }
    } catch (error) {
      resultDiv.innerHTML = `<div style="color: red;">❌ Error: ${error.message || 'Something went wrong'}</div>`;
    } finally {
      // Re-enable submit button
      submitButton.disabled = false;
      submitButton.textContent = "Schedule Automation";
    }
  });