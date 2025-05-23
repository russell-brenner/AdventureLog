<script>
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  let showModal = false;
  let jsonData = '';
  let errorMessage = '';
  let selectedFile = null; // Holds the File object
  let selectedFileType = ''; // 'json', 'csv', or ''

  export function openModal() {
    showModal = true;
    jsonData = '';
    errorMessage = '';
    selectedFile = null;
    selectedFileType = '';
    // Reset file input if it exists
    const fileInput = document.getElementById('importFile');
    if (fileInput) {
      fileInput.value = '';
    }
  }

  function closeModal() {
    showModal = false;
  }

  function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.name.endsWith('.json') || file.type === 'application/json') {
        selectedFile = file;
        selectedFileType = 'json';
        errorMessage = '';
      } else if (file.name.endsWith('.csv') || file.type === 'text/csv') {
        selectedFile = file;
        selectedFileType = 'csv';
        errorMessage = '';
      } else {
        selectedFile = null;
        selectedFileType = '';
        errorMessage = 'Invalid file type. Please select a JSON or CSV file.';
      }
      jsonData = ''; // Clear textarea if file is selected
    } else {
      selectedFile = null;
      selectedFileType = '';
    }
  }

  async function handleImport() {
    errorMessage = '';

    if (selectedFile) {
      try {
        const fileContent = await selectedFile.text();
        if (selectedFileType === 'json') {
          const parsedData = JSON.parse(fileContent);
          dispatch('import', { type: 'json', data: parsedData });
          closeModal();
        } else if (selectedFileType === 'csv') {
          dispatch('import', { type: 'csv', data: fileContent });
          closeModal();
        } else {
          // This case should ideally be caught by handleFileSelect, but as a safeguard:
          errorMessage = 'Invalid file type selected. Please select JSON or CSV.';
          return;
        }
      } catch (error) {
        if (selectedFileType === 'json') {
          errorMessage = 'Error parsing JSON file: ' + error.message;
        } else {
          errorMessage = 'Error reading file: ' + error.message;
        }
        return;
      }
    } else { // Textarea input (JSON only)
      if (!jsonData.trim()) {
        errorMessage = 'No data to import. Please select a file or paste JSON content.';
        return;
      }
      try {
        const parsedData = JSON.parse(jsonData);
        dispatch('import', { type: 'json', data: parsedData });
        closeModal();
      } catch (error) {
        errorMessage = 'Invalid JSON data in textarea: ' + error.message;
      }
    }
  }
</script>

{#if showModal}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 transition-opacity duration-300 ease-in-out"
    class:opacity-100={showModal}
    class:opacity-0={!showModal}
    on:click|self={closeModal}
  >
    <div
      class="bg-white p-6 rounded-lg shadow-xl w-full max-w-md transform transition-all duration-300 ease-in-out"
      class:scale-100={showModal}
      class:scale-95={!showModal}
      on:click|stopPropagation
    >
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-semibold text-gray-800">Import Collection</h2>
        <button on:click={closeModal} class="text-gray-500 hover:text-gray-700 text-2xl leading-none">&times;</button>
      </div>
      
      <div class="mb-4">
        <label for="importFile" class="block text-sm font-medium text-gray-700 mb-1">Upload JSON or CSV File</label>
        <input
          type="file"
          id="importFile"
          accept=".json,.csv,application/json,text/csv"
          on:change={handleFileSelect}
          class="w-full text-sm text-gray-500
                 file:mr-4 file:py-2 file:px-4
                 file:rounded-md file:border-0
                 file:text-sm file:font-semibold
                 file:bg-blue-50 file:text-blue-700
                 hover:file:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div class="text-center my-3 text-sm text-gray-500">OR</div>

      <div>
        <label for="jsonDataText" class="block text-sm font-medium text-gray-700 mb-1">Paste JSON Data</label>
        <textarea
          id="jsonDataText"
          bind:value={jsonData}
          rows="8"
          class="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Paste JSON content here. For CSV, please use the file upload option."
          on:input={() => { selectedFile = null; selectedFileType = ''; errorMessage = ''; }}
        ></textarea>
      </div>

      {#if errorMessage}
        <p class="text-red-500 text-sm mt-3 mb-3">{errorMessage}</p>
      {/if}

      <div class="mt-6 flex justify-end space-x-3">
        <button
          on:click={closeModal}
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 transition-colors"
        >
          Cancel
        </button>
        <button
          on:click={handleImport}
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        >
          Import
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Ensure the modal backdrop is correctly layered */
  .fixed.inset-0.z-50 {
    z-index: 50; /* Ensure this is higher than other content but lower than the modal dialog */
  }
  .fixed.inset-0.z-50 > div {
    z-index: 51; /* Ensure modal dialog is above the backdrop */
  }
</style>
