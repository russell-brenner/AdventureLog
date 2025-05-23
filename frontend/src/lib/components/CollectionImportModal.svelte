<script lang="ts">
  import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';

  const dispatch = createEventDispatcher();

  let showModal = false;
  let jsonData = '';
  let errorMessage = '';
  let selectedFile = null;

  let modal: HTMLDialogElement;

	console.log('Entering CollectionImportModal');

	onMount(async () => {
  	console.log('Entering onMount');
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();

      showModal = true;
      jsonData = '';
      errorMessage = '';
      selectedFile = null;
      // Reset file input if it exists
      const fileInput = document.getElementById('jsonFile');
      if (fileInput) {
        fileInput.value = '';
      }
		}
	});

  export function openModal() {
  	console.log('Entering openModal');
    showModal = true;
    jsonData = '';
    errorMessage = '';
    selectedFile = null;
    // Reset file input if it exists
    const fileInput = document.getElementById('jsonFile');
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
      selectedFile = files[0];
      jsonData = ''; // Clear textarea if file is selected
      errorMessage = '';
    } else {
      selectedFile = null;
    }
  }

  async function handleImport() {
    errorMessage = '';
    let dataToParse = jsonData;

    if (selectedFile) {
      try {
        dataToParse = await selectedFile.text();
      } catch (error) {
        errorMessage = 'Error reading file: ' + error.message;
        return;
      }
    }

    if (!dataToParse.trim()) {
      errorMessage = 'No data to import. Please select a file or paste JSON.';
      return;
    }

    try {
      const parsedData = JSON.parse(dataToParse);
      dispatch('import', parsedData);
      closeModal();
    } catch (error) {
      errorMessage = 'Invalid JSON data: ' + error.message;
    }
  }
</script>

<!-- {#if showModal} -->
<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
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
        <label for="jsonFile" class="block text-sm font-medium text-gray-700 mb-1">Upload JSON File (Optional)</label>
        <input
          type="file"
          id="jsonFile"
          accept=".json"
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
          placeholder="Paste JSON data here..."
          on:input={() => { selectedFile = null; errorMessage = ''; }}
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
<!-- {/if} -->
</dialog>

<style>
  /* Ensure the modal backdrop is correctly layered */
  .fixed.inset-0.z-50 {
    z-index: 50; /* Ensure this is higher than other content but lower than the modal dialog */
  }
  .fixed.inset-0.z-50 > div {
    z-index: 51; /* Ensure modal dialog is above the backdrop */
  }
</style>
