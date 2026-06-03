/**
 * S-08 Settings — Integrations
 * Connect GitHub, GitLab, Jira, Linear, notification channels.
 * Access: Org Admin only.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/org/integrations
 *   DELETE /api/v1/org/integrations/:integration_id
 */

import { useState } from "react";
import { CheckCircle2, AlertCircle, RefreshCw, Trash2, Plus, ChevronRight } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const INTEGRATIONS = {
  vcs:[
    {id:"gh1",name:"GitHub",icon:"🐙",status:"connected",repos:4,last_sync:"2min ago",connected_by:"Adnan K",scopes:["contents:read","pull_requests:read","metadata:read"]},
    {id:"gl1",name:"GitLab",icon:"🦊",status:"not_connected",repos:0,last_sync:null,connected_by:null,scopes:[]},
    {id:"bb1",name:"Bitbucket",icon:"🪣",status:"not_connected",repos:0,last_sync:null,connected_by:null,scopes:[]},
  ],
  ticketing:[
    {id:"jira1",name:"Jira",icon:"🎯",status:"connected",tickets:847,sprints:12,last_sync:"5min ago",connected_by:"Adnan K"},
    {id:"linear1",name:"Linear",icon:"⬡",status:"not_connected",tickets:0,sprints:0,last_sync:null,connected_by:null},
    {id:"gh_issues",name:"GitHub Issues",icon:"📋",status:"auto",tickets:0,sprints:0,last_sync:"via GitHub",connected_by:"auto"},
  ],
  ai_tools:[
    {id:"cc1",name:"Claude Code",icon:"⚡",status:"active",note:"Reads local JSONL — no API required",config:null},
    {id:"cur1",name:"Cursor",icon:"🖱",status:"active",note:"Reads local SQLite — no API required",config:null},
    {id:"kiro1",name:"Kiro",icon:"☁",status:"configured",note:"AWS S3 bucket configured",config:{bucket:"kiro-analytics-rapyder",role:"arn:aws:iam::123:role/KiroRead"}},
    {id:"cop1",name:"Copilot",icon:"🤖",status:"configured",note:"GitHub org connected for usage API",config:{org:"rapyder-cloud"}},
  ],
  notifications:[
    {id:"slack1",name:"Slack",icon:"💬",status:"connected",workspace:"Rapyder Engineering",last_used:"1h ago"},
    {id:"teams1",name:"Microsoft Teams",icon:"🔷",status:"not_connected",workspace:null,last_used:null},
    {id:"email1",name:"Email",icon:"✉",status:"always_on",workspace:"adnan@company.com",last_used:"always"},
    {id:"gchat1",name:"Google Chat",icon:"💭",status:"not_connected",workspace:null,last_used:null},
  ],
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}

function StatusBadge({status}:{status:string}){
  const cfg={
    connected:{c:C.green,bg:C.greenBg,l:"Connected"},
    configured:{c:C.accent,bg:C.accentBg,l:"Configured"},
    active:{c:C.green,bg:C.greenBg,l:"Active"},
    always_on:{c:C.sub,bg:"rgba(90,90,90,0.1)",l:"Always on"},
    auto:{c:C.purple,bg:"rgba(167,139,250,0.08)",l:"Auto"},
    not_connected:{c:C.sub,bg:"transparent",l:"Not connected"},
  }[status]??{c:C.sub,bg:"transparent",l:status};
  return <span style={{padding:"2px 7px",borderRadius:4,background:cfg.bg,color:cfg.c,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{cfg.l}</span>;
}

function IntegrationRow({item,type}:{item:any;type:string}){
  const [hov,setHov]=useState(false);
  const isConnected=item.status!=="not_connected";
  return(
    <div onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)}
      style={{display:"flex",alignItems:"center",gap:14,padding:"13px 18px",background:hov?C.hover:"transparent",transition:"background .1s"}}>
      <div style={{width:36,height:36,borderRadius:8,background:C.surface,border:`1px solid ${C.border}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,flexShrink:0}}>
        {item.icon}
      </div>
      <div style={{flex:1}}>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
          <span style={{fontFamily:F.body,fontSize:13,color:C.text,fontWeight:500}}>{item.name}</span>
          <StatusBadge status={item.status}/>
        </div>
        {isConnected&&item.last_sync&&(
          <div style={{fontFamily:F.body,fontSize:11,color:C.sub}}>
            Last sync: {item.last_sync}
            {item.repos&&` · ${item.repos} repos`}
            {item.tickets&&` · ${item.tickets} tickets, ${item.sprints} sprints`}
            {item.workspace&&` · ${item.workspace}`}
            {item.connected_by&&item.connected_by!=="auto"&&` · by ${item.connected_by}`}
            {item.note&&` · ${item.note}`}
          </div>
        )}
        {!isConnected&&<div style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{item.note||"Click to connect"}</div>}
        {item.config&&<div style={{fontFamily:F.mono,fontSize:10,color:C.sub,marginTop:2}}>{Object.entries(item.config).map(([k,v])=>`${k}: ${v}`).join(" · ")}</div>}
      </div>
      <div style={{display:"flex",gap:8,alignItems:"center"}}>
        {isConnected&&item.status!=="always_on"&&item.status!=="auto"&&item.status!=="active"&&(
          <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 9px",cursor:"pointer",color:C.sub,display:"flex",alignItems:"center",gap:4,fontFamily:F.body,fontSize:11}}>
            <RefreshCw size={11}/> Sync
          </button>
        )}
        {isConnected&&item.status!=="always_on"&&item.status!=="auto"&&item.status!=="active"&&(
          <button style={{background:"none",border:`1px solid rgba(255,69,69,0.2)`,borderRadius:6,padding:"5px 9px",cursor:"pointer",color:C.red,display:"flex",alignItems:"center",gap:4,fontFamily:F.body,fontSize:11}}>
            <Trash2 size={11}/> Disconnect
          </button>
        )}
        {!isConnected&&(
          <button style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.25)`,borderRadius:6,padding:"5px 12px",cursor:"pointer",color:C.accent,fontFamily:F.body,fontSize:11,display:"flex",alignItems:"center",gap:5}}>
            <Plus size={11}/> Connect
          </button>
        )}
      </div>
    </div>
  );
}

function Section({title,sub,children}:{title:string;sub:string;children:React.ReactNode}){
  return(
    <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
      <div style={{padding:"14px 18px 10px"}}>
        <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>{title}</div>
        <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>{sub}</div>
      </div>
      <Divider/>
      {children}
    </div>
  );
}

export default function SettingsIntegrations(){
  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px"}}>
          <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Settings · Integrations</div>
          <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Integrations</h1>
          <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>Connect your repositories, ticketing tools, AI coding tools, and notification channels</div>
        </div>
        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          <Section title="Version Control" sub="Connect your git repositories to enable branch-based attribution and PR tracking">
            {INTEGRATIONS.vcs.map((item,i)=>(
              <div key={i}><IntegrationRow item={item} type="vcs"/>{i<INTEGRATIONS.vcs.length-1&&<Divider/>}</div>
            ))}
          </Section>
          <Section title="Ticketing & Sprint Tracking" sub="Connect your project management tools to attribute AI sessions to tickets, epics, and sprints">
            {INTEGRATIONS.ticketing.map((item,i)=>(
              <div key={i}><IntegrationRow item={item} type="ticketing"/>{i<INTEGRATIONS.ticketing.length-1&&<Divider/>}</div>
            ))}
          </Section>
          <Section title="AI Tool Setup" sub="Source 2 configuration — billing API access for cost reconciliation per tool">
            {INTEGRATIONS.ai_tools.map((item,i)=>(
              <div key={i}><IntegrationRow item={item} type="ai_tools"/>{i<INTEGRATIONS.ai_tools.length-1&&<Divider/>}</div>
            ))}
          </Section>
          <Section title="Notification Channels" sub="Where to send alerts, weekly digests, and agent install links">
            {INTEGRATIONS.notifications.map((item,i)=>(
              <div key={i}><IntegrationRow item={item} type="notifications"/>{i<INTEGRATIONS.notifications.length-1&&<Divider/>}</div>
            ))}
          </Section>
        </div>
      </div>
    </>
  );
}
