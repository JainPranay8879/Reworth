let currentStep=1,totalSteps=4;
function openModal(id){document.getElementById(id)?.classList.add('open')}function closeModal(id){document.getElementById(id)?.classList.remove('open')}function swapModal(a,b){closeModal(a);openModal(b)}
function closeResult(){const m=document.getElementById('resultModal');if(m){m.classList.remove('open');m.setAttribute('aria-hidden','true')}}
function showStep(n){currentStep=n;document.querySelectorAll('.form-step').forEach(e=>e.classList.toggle('active',+e.dataset.step===n));document.getElementById('stepLabel').textContent=`Step ${n} of ${totalSteps}`;document.getElementById('qualityLabel').textContent=n===4?'Almost there':'A few thoughtful questions';document.getElementById('progressBar').style.width=`${n/totalSteps*100}%`;document.getElementById('backBtn').hidden=n===1;document.getElementById('nextBtn').hidden=n===totalSteps;document.getElementById('submitBtn').hidden=n!==totalSteps;window.scrollTo({top:0,behavior:'smooth'})}
function validStep(){const s=document.querySelector(`.form-step[data-step="${currentStep}"]`);for(const f of s.querySelectorAll('input,select,textarea'))if(!f.checkValidity()){f.reportValidity();return false}return true}
function factorLabel(k){return({condition:'Condition',age:'Age & useful life',problem:'Problem severity',history:'Repair history',economics:'Cost comparison',repairability:'Repairability signal'})[k]||k}
function renderFactors(c){const box=document.getElementById('factorList');box.innerHTML='';const limits={condition:31,age:12,problem:9,history:10,economics:18,repairability:8};Object.entries(c||{}).forEach(([k,v])=>{const r=document.createElement('div');r.className='factor-row';const limit=limits[k]||18;const width=Math.min(100,Math.round(Math.abs(v)/limit*100));const cls=v>0?'positive':v<0?'negative':'neutral';r.innerHTML=`<div class="factor-main"><span>${factorLabel(k)}</span><strong class="${cls}">${v>0?'+':''}${v}</strong></div><div class="factor-track"><i class="${cls}" style="width:${width}%"></i></div><small>${v>0?'Supports the decision':v<0?'Pulls the score down':'Little effect on the score'}</small>`;box.appendChild(r)})}
async function submitAssessment(e){e.preventDefault();if(!validStep())return;const b=document.getElementById('submitBtn');b.disabled=true;b.classList.add('loading');try{const r=await fetch('/api/assess',{method:'POST',body:new FormData(e.target)}),x=await r.json();if(!r.ok)throw Error(x.error||'Something went wrong.');document.getElementById('decisionText').textContent=x.decision;document.getElementById('scoreText').textContent=x.score;document.getElementById('confidenceText').textContent=x.confidence;document.getElementById('qualityText').textContent=`Information quality: ${x.quality}%`;document.getElementById('reasonText').textContent=x.reason;document.getElementById('nextStepText').textContent=x.next_step;document.getElementById('resultHeadline').textContent=x.decision==='Diagnosis Required'?'We need a little more information before making a confident call.':'A transparent assessment based on the information you provided.';document.getElementById('resultIcon').textContent=({Repair:'↻',Reuse:'↺',Donate:'♡',Recycle:'♻',Replace:'→','Diagnosis Required':'?'})[x.decision]||'•';renderFactors(x.components);const m=document.getElementById('resultModal');m.classList.add('open');m.setAttribute('aria-hidden','false')}catch(err){alert(err.message)}finally{b.disabled=false;b.classList.remove('loading')}}
document.addEventListener('DOMContentLoaded',()=>{const f=document.getElementById('assessmentForm');if(!f)return;document.getElementById('nextBtn').onclick=()=>{if(validStep())showStep(Math.min(totalSteps,currentStep+1))};document.getElementById('backBtn').onclick=()=>showStep(Math.max(1,currentStep-1));f.addEventListener('submit',submitAssessment);showStep(1)})


// Password visibility controls — available on login, registration, account and reset forms.
function setupPasswordToggles(){
  document.querySelectorAll('input[type="password"]').forEach((input, index)=>{
    if(input.dataset.passwordToggleReady) return;
    input.dataset.passwordToggleReady='true';
    const wrapper=document.createElement('div');
    wrapper.className='password-field';
    input.parentNode.insertBefore(wrapper,input);
    wrapper.appendChild(input);
    const button=document.createElement('button');
    button.type='button';
    button.className='password-toggle';
    button.setAttribute('aria-label','Show password');
    button.setAttribute('aria-pressed','false');
    button.innerHTML='<span aria-hidden="true">◉</span><span class="password-toggle-text">Show</span>';
    button.addEventListener('click',()=>{
      const visible=input.type==='text';
      input.type=visible?'password':'text';
      button.setAttribute('aria-label',visible?'Show password':'Hide password');
      button.setAttribute('aria-pressed',String(!visible));
      button.querySelector('.password-toggle-text').textContent=visible?'Show':'Hide';
      button.querySelector('span').textContent=visible?'◉':'◉';
    });
    wrapper.appendChild(button);
  });
}

document.addEventListener('DOMContentLoaded',setupPasswordToggles);
