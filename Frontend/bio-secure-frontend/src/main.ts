import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
export const supabase = createClient(supabaseUrl, supabaseKey);

createApp(App).use(router).mount('#app')
