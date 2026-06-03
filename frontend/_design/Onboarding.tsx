/**
 * S-19 to S-24 — Onboarding Flow (all 6 steps in one file)
 * Steps: Welcome → Connect → Configure → Add Team → Install Agent → First Session
 *
 * REAL API CONTRACT:
 *   GET  /api/v1/onboarding/status
 *   POST /api/v1/onboarding/connect-github
 *   POST /api/v1/onboarding/connect-ticketing
 *   POST /api/v1/onboarding/configure-tools
 *   POST /api/v1/onboarding/invite-team
 *   GET  /api/v1/onboarding/agent-installs (SSE)
 *   GET  /api/v1/onboarding/first-session  (SSE)
 */

import { useState, useEffect } from "react";
import { CheckCircle2, Circle, ArrowRight, Zap, GitBranch, Settings, Users, Download, Sparkles, ChevronRight, Copy } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",purple:"#A78BFA",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const STEPS=[
  {n:1,label:"Connect repos",icon:GitBranch},
  {n:2,label:"Configure AI tools",icon:Settings},
  {n:3,label:"Add team",icon:Users},
  {n:4,label:"Install agent",icon:Download},
  {n:5,label:"First session",icon:Zap},
];

function Divider(){return <div style={{height:1,background:C.border}}/>;}

function ProgressBar({current}:{current:number}){
  return(
    <div style={{display:"flex",alignItems:"center",gap:0,marginBottom:40}}>
      {STEPS.map((s,i)=>{
        const done=s.n<current;const active=s.n===current;
        return(
          <div key={i} style={{display:"flex",alignItems:"center",flex:i<STEPS.length-1?1:"auto"}}>
            <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:6}}>
              <div style={{width:28,height:28,borderRadius:"50%",background:done?C.accentBg:active?C.accentBg:C.surface,border:`2px solid ${done?C.accent:active?C.accent:C.border}`,display:"flex",alignItems:"center",justifyContent:"center",transition:"all .3s"}}>
                {done?<CheckCircle2 size={14} color={C.accent}/>:<s.icon size={12} color={active?C.accent:C.sub}/>}
              </div>
              <span style={{fontFamily:F.body,fontSize:10,color:active?C.text:C.sub,whiteSpace:"nowrap"}}>{s.label}</span>
            </div>
            {i<STEPS.length-1&&<div style={{flex:1,height:2,background:done?C.accent:C.muted,marginBottom:18,marginLeft:6,marginRight:6,transition:"background .3s"}}/>}
          </div>
        );
      })}
    </div>
  );
}

// Step 0 — Welcome
function StepWelcome({onNext}:{onNext:()=>void}){
  return(
    <div style={{textAlign:"center"}}>
      <div style={{width:64,height:64,borderRadius:16,background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,display:"flex",alignItems:"center",justifyContent:"center",margin:"0 auto 20px"}}>
        <Zap size={28} color={C.accent}/>
      </div>
      <div style={{fontFamily:F.ui,fontSize:28,fontWeight:700,color:C.text,letterSpacing:"-0.02em",marginBottom:10}}>Welcome to [Product]</div>
      <div style={{fontFamily:F.body,fontSize:15,color:C.sub,marginBottom:36}}>Let's set up your workspace. Takes about 10 minutes.</div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12,marginBottom:36}}>
        {[
          {icon:"💰",title:"Cost per ticket",desc:"See exact AI spend attributed to every Jira ticket"},
          {icon:"⚠️",title:"Loop detection",desc:"Catch developers stuck in hallucination loops early"},
          {icon:"📊",title:"Prove ROI",desc:"Financial-grade reporting for engineering AI spend"},
        ].map((card,i)=>(
          <div key={i} style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"16px 14px",textAlign:"left"}}>
            <div style={{fontSize:22,marginBottom:8}}>{card.icon}</div>
            <div style={{fontFamily:F.body,fontSize:13,color:C.text,fontWeight:500,marginBottom:4}}>{card.title}</div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,lineHeight:1.5}}>{card.desc}</div>
          </div>
        ))}
      </div>
      <button onClick={onNext} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"13px 32px",cursor:"pointer",fontFamily:F.body,fontSize:14,color:C.accent,fontWeight:500,display:"inline-flex",alignItems:"center",gap:8}}>
        Connect your repositories <ArrowRight size={15}/>
      </button>
    </div>
  );
}

// Step 1 — Connect repos
function StepConnect({onNext}:{onNext:()=>void}){
  const [ghConnected,setGhConnected]=useState(false);
  const [jiraConnected,setJiraConnected]=useState(false);
  const [backfilling,setBackfilling]=useState(false);
  const [backfillPct,setBackfillPct]=useState(0);

  useEffect(()=>{
    if(ghConnected&&!backfilling){
      setBackfilling(true);
      const iv=setInterval(()=>{
        setBackfillPct(p=>{if(p>=100){clearInterval(iv);return 100;}return p+2;});
      },80);
    }
  },[ghConnected]);

  return(
    <div>
      <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,marginBottom:6}}>Connect your repositories</div>
      <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:24}}>Connect GitHub and your ticketing tool to enable AI session attribution</div>

      <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,marginBottom:12,overflow:"hidden"}}>
        <div style={{padding:"16px"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:ghConnected?12:0}}>
            <div style={{display:"flex",gap:12,alignItems:"center"}}>
              <span style={{fontSize:22}}>🐙</span>
              <div><div style={{fontFamily:F.body,fontSize:14,color:C.text,fontWeight:500}}>GitHub</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Connect via GitHub App for branch tracking and PR data</div></div>
            </div>
            {!ghConnected
              ?<button onClick={()=>setGhConnected(true)} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,borderRadius:7,padding:"8px 16px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.accent}}>Connect GitHub →</button>
              :<span style={{fontFamily:F.mono,fontSize:11,color:C.green}}>✓ 4 repos connected</span>}
          </div>
          {ghConnected&&(
            <div style={{background:C.surface,borderRadius:7,padding:"10px 12px"}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Importing last 90 days of tickets and PRs…</span>
                <span style={{fontFamily:F.mono,fontSize:11,color:C.accent}}>{backfillPct}%</span>
              </div>
              <div style={{height:4,background:C.muted,borderRadius:2,overflow:"hidden"}}>
                <div style={{height:"100%",width:`${backfillPct}%`,background:C.accent,borderRadius:2,transition:"width .1s"}}/>
              </div>
              {backfillPct===100&&<div style={{fontFamily:F.body,fontSize:11,color:C.green,marginTop:5}}>✓ 847 tickets, 12 sprints, 34 PRs imported</div>}
              {backfillPct<100&&<div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:4}}>This sets your baseline. AI costs appear after agents are installed.</div>}
            </div>
          )}
        </div>
      </div>

      {ghConnected&&(
        <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,marginBottom:20,padding:"16px"}}>
          <div style={{fontFamily:F.body,fontSize:13,color:C.text,fontWeight:500,marginBottom:12}}>Connect ticketing</div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10}}>
            {[{name:"Jira",icon:"🎯",note:"OAuth"},{name:"Linear",icon:"⬡",note:"OAuth"},{name:"GitHub Issues",icon:"📋",note:"Auto (free)"}].map((t,i)=>(
              <button key={i} onClick={()=>setJiraConnected(true)} style={{background:jiraConnected&&t.name==="Jira"?C.accentBg:C.surface,border:`1px solid ${jiraConnected&&t.name==="Jira"?"rgba(0,212,255,0.3)":C.border}`,borderRadius:8,padding:"12px",cursor:"pointer",textAlign:"left"}}>
                <div style={{fontSize:18,marginBottom:6}}>{t.icon}</div>
                <div style={{fontFamily:F.body,fontSize:12,color:C.text,fontWeight:500}}>{t.name}</div>
                <div style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{jiraConnected&&t.name==="Jira"?"Connected ✓":t.note}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <button onClick={onNext} disabled={!ghConnected} style={{background:ghConnected?C.accentBg:"rgba(0,0,0,0.3)",border:`1px solid ${ghConnected?"rgba(0,212,255,0.35)":C.border}`,borderRadius:9,padding:"12px 24px",cursor:ghConnected?"pointer":"default",fontFamily:F.body,fontSize:13,color:ghConnected?C.accent:C.sub,display:"flex",alignItems:"center",gap:7}}>
        Continue <ArrowRight size={14}/>
      </button>
    </div>
  );
}

// Step 2 — Configure tools
function StepConfigure({onNext}:{onNext:()=>void}){
  const [selected,setSelected]=useState<string[]>(["claude-code","cursor"]);
  const toggle=(t:string)=>setSelected(p=>p.includes(t)?p.filter(x=>x!==t):[...p,t]);
  const tools=[
    {id:"claude-code",name:"Claude Code",icon:"⚡",note:"Reads local JSONL — no API needed"},
    {id:"cursor",name:"Cursor",icon:"🖱",note:"Reads local SQLite — no API needed"},
    {id:"kiro",name:"Kiro",icon:"☁",note:"Requires AWS S3 bucket for cost data"},
    {id:"copilot",name:"Copilot",icon:"🤖",note:"Requires GitHub org connection"},
  ];
  return(
    <div>
      <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,marginBottom:6}}>Which AI tools does your team use?</div>
      <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:24}}>The agent will capture sessions from selected tools. You can configure per-team later.</div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:20}}>
        {tools.map(t=>(
          <div key={t.id} onClick={()=>toggle(t.id)} style={{background:selected.includes(t.id)?C.accentBg:C.card,border:`1px solid ${selected.includes(t.id)?"rgba(0,212,255,0.3)":C.border}`,borderRadius:9,padding:"14px",cursor:"pointer",display:"flex",gap:12,alignItems:"flex-start",transition:"all .15s"}}>
            <span style={{fontSize:20}}>{t.icon}</span>
            <div style={{flex:1}}>
              <div style={{fontFamily:F.body,fontSize:13,color:C.text,fontWeight:500,marginBottom:3}}>{t.name}</div>
              <div style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{t.note}</div>
            </div>
            <div style={{width:18,height:18,borderRadius:"50%",background:selected.includes(t.id)?C.accentBg:"transparent",border:`2px solid ${selected.includes(t.id)?C.accent:C.border}`,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
              {selected.includes(t.id)&&<div style={{width:8,height:8,borderRadius:"50%",background:C.accent}}/>}
            </div>
          </div>
        ))}
      </div>
      {selected.includes("kiro")&&(
        <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"14px",marginBottom:14}}>
          <div style={{fontFamily:F.body,fontSize:12,color:C.text,fontWeight:500,marginBottom:10}}>Kiro — AWS S3 Setup</div>
          {["S3 bucket name","IAM role ARN"].map(l=>(
            <div key={l} style={{marginBottom:8}}>
              <label style={{fontFamily:F.body,fontSize:11,color:C.sub,display:"block",marginBottom:4}}>{l}</label>
              <input placeholder={l==="S3 bucket name"?"kiro-analytics-yourorg":"arn:aws:iam::123:role/KiroRead"} style={{width:"100%",background:C.surface,border:`1px solid ${C.border}`,borderRadius:7,padding:"9px 12px",fontFamily:F.mono,fontSize:11,color:C.text,outline:"none"}}/>
            </div>
          ))}
        </div>
      )}
      <button onClick={onNext} disabled={selected.length===0} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"12px 24px",cursor:"pointer",fontFamily:F.body,fontSize:13,color:C.accent,display:"flex",alignItems:"center",gap:7}}>
        Continue <ArrowRight size={14}/>
      </button>
    </div>
  );
}

// Step 3 — Add team
function StepAddTeam({onNext}:{onNext:()=>void}){
  const [emails,setEmails]=useState("sara@company.com\nraj@company.com\npriya@company.com");
  const [sent,setSent]=useState(false);
  const parsed=emails.split("\n").filter(e=>e.trim()&&e.includes("@"));
  return(
    <div>
      <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,marginBottom:6}}>Add your team members</div>
      <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:24}}>They'll receive a Slack or email invite with a personalised agent install command</div>
      {!sent?(
        <>
          <label style={{fontFamily:F.body,fontSize:12,color:C.sub,display:"block",marginBottom:6}}>Paste emails or GitHub usernames</label>
          <textarea value={emails} onChange={e=>setEmails(e.target.value)} rows={5} style={{width:"100%",background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"12px 14px",fontFamily:F.mono,fontSize:12,color:C.text,outline:"none",resize:"vertical",marginBottom:14}}/>
          <div style={{display:"flex",gap:16,marginBottom:20,alignItems:"center"}}>
            <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>Default role:</span>
            <select style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:6,padding:"6px 12px",fontFamily:F.body,fontSize:12,color:C.text,outline:"none",cursor:"pointer"}}>
              <option>Developer</option><option>Team Lead</option>
            </select>
            <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>{parsed.length} member{parsed.length!==1?"s":""} found</span>
          </div>
          <div style={{display:"flex",gap:10}}>
            <button onClick={()=>setSent(true)} disabled={parsed.length===0} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"12px 24px",cursor:"pointer",fontFamily:F.body,fontSize:13,color:C.accent,display:"flex",alignItems:"center",gap:7}}>
              Send invitations <ArrowRight size={14}/>
            </button>
            <button onClick={onNext} style={{background:"none",border:`1px solid ${C.border}`,borderRadius:9,padding:"12px 20px",cursor:"pointer",fontFamily:F.body,fontSize:13,color:C.sub}}>
              Skip for now
            </button>
          </div>
        </>
      ):(
        <div>
          <div style={{background:C.greenBg,border:`1px solid rgba(0,230,118,0.2)`,borderRadius:9,padding:"14px 16px",marginBottom:20,display:"flex",gap:10,alignItems:"center"}}>
            <CheckCircle2 size={16} color={C.green}/>
            <span style={{fontFamily:F.body,fontSize:13,color:C.text}}>Invitations sent to {parsed.length} team members via email</span>
          </div>
          <button onClick={onNext} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"12px 24px",cursor:"pointer",fontFamily:F.body,fontSize:13,color:C.accent,display:"flex",alignItems:"center",gap:7}}>
            Continue to agent install <ArrowRight size={14}/>
          </button>
        </div>
      )}
    </div>
  );
}

// Step 4 — Install agent
function StepInstall({onNext}:{onNext:()=>void}){
  const [os,setOs]=useState<"win"|"mac"|"linux">("win");
  const [copied,setCopied]=useState(false);
  const cmds={
    win:`iwr https://get.[product].io/install.ps1 | iex -OrgToken ORG_TOKEN_HERE`,
    mac:`curl -fsSL https://get.[product].io/install.sh | sh -s ORG_TOKEN_HERE`,
    linux:`curl -fsSL https://get.[product].io/install.sh | sh -s ORG_TOKEN_HERE`,
  };
  const installs=[
    {name:"Adnan K",status:"installed",time:"Just now"},
    {name:"Sara P",status:"pending",time:"Invited 2min ago"},
    {name:"Raj K",status:"pending",time:"Invited 2min ago"},
    {name:"Priya M",status:"pending",time:"Invited 2min ago"},
  ];
  return(
    <div>
      <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,marginBottom:6}}>Install the agent</div>
      <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:24}}>Run this command on each developer machine. Takes 2 minutes.</div>
      <div style={{display:"flex",gap:4,background:C.surface,borderRadius:8,padding:4,marginBottom:12,width:"fit-content"}}>
        {([["win","Windows"],["mac","Mac"],["linux","Linux"]] as const).map(([k,l])=>(
          <button key={k} onClick={()=>setOs(k)} style={{background:os===k?C.card:"none",border:`1px solid ${os===k?C.border:"transparent"}`,borderRadius:6,padding:"6px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:os===k?C.text:C.sub}}>{l}</button>
        ))}
      </div>
      <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"16px",marginBottom:14,position:"relative"}}>
        <div style={{fontFamily:F.mono,fontSize:12,color:C.accent,wordBreak:"break-all",lineHeight:1.6,paddingRight:40}}>{cmds[os]}</div>
        <button onClick={()=>{setCopied(true);setTimeout(()=>setCopied(false),2000);}} style={{position:"absolute",top:12,right:12,background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"4px 8px",cursor:"pointer",fontFamily:F.body,fontSize:10,color:C.sub,display:"flex",alignItems:"center",gap:4}}>
          <Copy size={10}/> {copied?"Copied!":"Copy"}
        </button>
      </div>
      <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"14px",marginBottom:20}}>
        <div style={{fontFamily:F.body,fontSize:12,color:C.text,fontWeight:500,marginBottom:10}}>Install status</div>
        {installs.map((m,i)=>(
          <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"7px 0",borderBottom:i<installs.length-1?`1px solid ${C.border}`:"none"}}>
            <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>{m.name}</span>
            <div style={{display:"flex",gap:8,alignItems:"center"}}>
              <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{m.time}</span>
              {m.status==="installed"?<span style={{fontFamily:F.mono,fontSize:11,color:C.green}}>✓ Installed</span>:<span style={{fontFamily:F.mono,fontSize:11,color:C.amber}}>Pending</span>}
            </div>
          </div>
        ))}
        <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:8}}>1 of {installs.length} agents installed · More will appear as developers install</div>
      </div>
      <button onClick={onNext} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"12px 24px",cursor:"pointer",fontFamily:F.body,fontSize:13,color:C.accent,display:"flex",alignItems:"center",gap:7}}>
        Continue <ArrowRight size={14}/>
      </button>
    </div>
  );
}

// Step 5 — First session
function StepFirstSession(){
  const [captured,setCaptured]=useState(false);
  useEffect(()=>{
    const t=setTimeout(()=>setCaptured(true),3000);
    return()=>clearTimeout(t);
  },[]);
  return(
    <div style={{textAlign:"center"}}>
      {!captured?(
        <>
          <div style={{position:"relative",width:80,height:80,margin:"0 auto 24px"}}>
            <div style={{position:"absolute",inset:0,borderRadius:"50%",border:`2px solid ${C.accent}`,opacity:0.3,animation:"ping 2s infinite"}}/>
            <div style={{width:80,height:80,borderRadius:"50%",background:C.accentBg,border:`2px solid rgba(0,212,255,0.3)`,display:"flex",alignItems:"center",justifyContent:"center"}}>
              <Zap size={28} color={C.accent}/>
            </div>
          </div>
          <style>{`@keyframes ping{0%{transform:scale(1);opacity:.3}70%{transform:scale(1.8);opacity:0}100%{transform:scale(2);opacity:0}}`}</style>
          <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,marginBottom:8}}>Waiting for first session…</div>
          <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:28}}>Open your AI coding tool and start working. The agent will capture the session automatically.</div>
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"16px",textAlign:"left",maxWidth:380,margin:"0 auto"}}>
            {[
              {l:"GitHub connected",done:true},{l:"Jira connected (847 tickets)",done:true},
              {l:"Tools configured (Claude Code, Cursor)",done:true},{l:"3 members invited",done:true},
              {l:"1 of 4 agents installed",done:true},{l:"First session captured",done:false},
            ].map((item,i)=>(
              <div key={i} style={{display:"flex",alignItems:"center",gap:10,padding:"6px 0",borderBottom:i<5?`1px solid ${C.border}`:"none"}}>
                {item.done?<CheckCircle2 size={14} color={C.green}/>:<Circle size={14} color={C.sub}/>}
                <span style={{fontFamily:F.body,fontSize:12,color:item.done?C.text:C.sub}}>{item.l}</span>
              </div>
            ))}
          </div>
        </>
      ):(
        <>
          <div style={{fontSize:56,marginBottom:20}}>🎉</div>
          <div style={{fontFamily:F.ui,fontSize:26,fontWeight:700,color:C.text,marginBottom:8}}>First session captured!</div>
          <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:24}}>Your team is live. AI costs are now being attributed to tickets.</div>
          <div style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.2)`,borderRadius:9,padding:"16px",display:"inline-block",textAlign:"left",marginBottom:28}}>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:6}}>First session attributed to</div>
            <div style={{fontFamily:F.mono,fontSize:14,color:C.accent,marginBottom:2}}>JIRA-142</div>
            <div style={{fontFamily:F.body,fontSize:12,color:C.text}}>Adnan K · Claude Code · 74min · $0.42</div>
            <div style={{fontFamily:F.mono,fontSize:10,color:C.green,marginTop:4}}>✓ 87% confidence · branch_parse</div>
          </div>
          <div style={{display:"flex",justifyContent:"center"}}>
            <button style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"13px 32px",cursor:"pointer",fontFamily:F.body,fontSize:14,color:C.accent,fontWeight:500,display:"flex",alignItems:"center",gap:8}}>
              View your dashboard <ArrowRight size={15}/>
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// Root onboarding component
export default function Onboarding(){
  const [step,setStep]=useState<0|1|2|3|4|5>(0);
  const next=()=>setStep(p=>(p<5?p+1:p) as any);

  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}input,textarea,select{font-family:'DM Sans',sans-serif}input::placeholder,textarea::placeholder{color:#5A5A5A}input:focus,textarea:focus{outline:none}select{cursor:pointer}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        {/* Top bar */}
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"14px 28px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{width:28,height:28,borderRadius:7,background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,display:"flex",alignItems:"center",justifyContent:"center"}}>
              <Zap size={14} color={C.accent}/>
            </div>
            <span style={{fontFamily:F.ui,fontSize:15,fontWeight:700,color:C.text}}>[Product]</span>
          </div>
          <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>14-day free trial · No card required</span>
        </div>

        <div style={{maxWidth:640,margin:"0 auto",padding:"48px 24px"}}>
          {step>0&&<ProgressBar current={step}/>}
          {step===0&&<StepWelcome onNext={next}/>}
          {step===1&&<StepConnect onNext={next}/>}
          {step===2&&<StepConfigure onNext={next}/>}
          {step===3&&<StepAddTeam onNext={next}/>}
          {step===4&&<StepInstall onNext={next}/>}
          {step===5&&<StepFirstSession/>}

          {/* Step navigation for demo */}
          {step>0&&step<5&&(
            <div style={{marginTop:32,paddingTop:20,borderTop:`1px solid ${C.border}`,display:"flex",justifyContent:"center",gap:6}}>
              {[1,2,3,4,5].map(s=>(
                <button key={s} onClick={()=>setStep(s as any)} style={{width:8,height:8,borderRadius:"50%",background:s===step?C.accent:C.muted,border:"none",cursor:"pointer",padding:0}}/>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
