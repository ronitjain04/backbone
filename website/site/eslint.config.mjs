import js from '@eslint/js';
import globals from 'globals';
export default [
 {ignores:['node_modules/**','dist/**','.openai/**']},
 js.configs.recommended,
 {files:['**/*.js','**/*.mjs'],languageOptions:{ecmaVersion:2022,sourceType:'module',globals:{...globals.browser,...globals.node}},rules:{'no-empty':['error',{allowEmptyCatch:true}],'no-unused-vars':['error',{args:'none',caughtErrors:'none'}]}}
];
