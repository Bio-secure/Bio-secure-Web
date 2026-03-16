// src/services/authService.js (updated)

import { reactive, watch } from 'vue';

// Initialize reactive state from localStorage if available
const authState = reactive({
  isLoggedIn: localStorage.getItem('isLoggedIn') === 'true',
  isAdmin: localStorage.getItem('isAdmin') === 'true',
  employeeId: localStorage.getItem('employeeId') || null,
  name: localStorage.getItem('name') || null,     // NEW
  surname: localStorage.getItem('surname') || null, // NEW
});

// Watch for changes and persist to localStorage
watch(authState, (newState) => {
  localStorage.setItem('isLoggedIn', newState.isLoggedIn);
  localStorage.setItem('isAdmin', newState.isAdmin);
  localStorage.setItem('employeeId', newState.employeeId || '');
  localStorage.setItem('name', newState.name || '');     // NEW
  localStorage.setItem('surname', newState.surname || ''); // NEW
});

// Update the login function to accept name and surname
export function login(employeeId, isAdmin, name, surname) { // MODIFIED
  authState.isLoggedIn = true;
  authState.isAdmin = isAdmin;
  authState.employeeId = employeeId;
  authState.name = name;         // NEW
  authState.surname = surname;   // NEW
}

export function logout() {
  authState.isLoggedIn = false;
  authState.isAdmin = false;
  authState.employeeId = null;
  authState.name = null;     // NEW
  authState.surname = null;  // NEW
  // Clear localStorage immediately for security
  localStorage.removeItem('isLoggedIn');
  localStorage.removeItem('isAdmin');
  localStorage.removeItem('employeeId');
  localStorage.removeItem('name');     // NEW
  localStorage.removeItem('surname');  // NEW
}

export default authState;