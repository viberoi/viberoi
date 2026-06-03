/**
 * S-15 Session Detail (drill-down)
 * The atomic unit of the product. Everything about one AI session.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/sessions/:session_id
 *   Coding agent: replace MOCK_SESSION with api.get('/sessions/'+id)
 */

import { useState } from "react";
import {
  ArrowLeft, GitCommit, Clock, DollarSign,
  FileCode, Zap, Shield, AlertTriangle,
  CheckCircle2, XCircle, ChevronRight,
} from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",purpleBg:"rgba(167,139,250,0.08)",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

// GET /api/v1/sessions/s_a2
const MOCK_SESSION = {
  session_id:"local_d7f613d2-dd58-4cc5-9238-a819ae844f4b",
  developer:{name:"Adnan K",email:"adnan@company.com",avatar:"AK",color:"#00D4FF"},
  tool:{name:"claude-code",surface:"desktop_app",version:"2.1.128",model:"claude-sonnet-4-6",capture_mode:"local_exact"},
  pricing:{type:"subscription",unit:"tokens",rate_usd:0.000003},
  timing:{started_at:"2026-05-28T09:28:35Z",ended_at:"2026-05-28T10:42:55Z",active_duration_min:74,first_commit_at:"2026-05-28T10:55:00Z",time_to_first_commit_min:86},
  tokens:{input:3,output:226,cache_read:163906,cache_write:188,total_cost_usd:0.42,is_estimated:false,reconciled:true,reconciled_at:"2026-05-28T11:00:00Z"},
  activity:{turn_count:12,mode:"agent",is_agentic:true,subagent_count:4,files_touched:["src/payments/gateway.ts","src/payments/stripe.ts",".husky/pre-commit","tests/payments.test.ts"],files_touched_count:4},
  code_output:{lines_added:47,lines_deleted:12,lines_accepted:38,lines_reverted:9,is_committed:true,commit_hashes:["7adc7be","ce34db2"],uncommitted_at_end:false},
  repository:{name:"wvp-backend",branch:"feature/JIRA-142-payment-gateway",raw_branch:"claude/xenodochial-joliot-361764",is_worktree:true},
  attribution:{ticket_id:"JIRA-142",ticket_title:"Implement Stripe payment gateway",epic_id:"EPIC-12",sprint_id:"SPRINT-42",confidence:0.87,signals:["branch_match","file_overlap","temporal_proximity"],method:"branch_parse"},
  quality:{session_restarts:0,file_oscillations:1,token_spike_detected:false,no_commit_duration_min:0,is_refunded:false,hallucination_risk:"none"},
  meta:{captured_at:"2026-05-28T10:43:00Z",agent_version:"0.1.0",data_sources:["local_jsonl","git_diff","worktree_map"],schema_version:"1.0"},
  // Turn-level token data (Claude Code only)
  turns:[
    {turn:1,input:1240,output:82,cache_read:0,cache_write:188,cost:0.004},
    {turn:2,input:180,output:24,cache_read:18200,cache_write:0,cost:0.001},
    {turn:3,input:92,output:41,cache_read:24100,cache_write:0,cost:0.001},
    {turn:4,input:76,output:18,cache_read:28400,cache_write:0,cost:0.001},
    {turn:5,input:48,output:22,cache_read:31200,cache_write:0,cost:0.001},
    {turn:6,input:62,output:15,cache_read:29800,cache_write:0,cost:0.001},
    {turn:7,input:44,output:8,cache_read:32100,cache_write:0,cost:0.000},
    {turn:8,input:38,output:6,cache_read:0,cache_write:0,cost:0.000},
    {turn:9,input:51,output:9,cache_read:0,cache_write:0,cost:0.000},
    {turn:10,input:29,output:1,cache_read:0,cache_write:0,cost:0.000},
    {turn:11,input:72,output:0,cache_read:0,cache_write:0,cost:0.000},
    {turn:12,input:44,output:0,cache_read:0,cache_write:0,cost:0.000},
  ],
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}
function StatCard({label,value,sub,color}:{label:string;value:string;sub?:string;color:string}){
  return(
    <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:8,padding:"12px 14px"}}>
      <div style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:5}}>{label}</div>
      <div style={{fontFamily:F.mono,fontSize:18,fontWeight:600,color,lineHeight:1,marginBottom:sub?3:0}}>{value}</div>
      {sub&&<div style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{sub}</div>}
    </div>
  );
}

export default function SessionDetail(){
  const session=MOCK_SESSION;
  const maxInput=Math.max(...session.turns.map(t=>t.input));

  const signalLabels:Record<string,string>={
    branch_match:"Branch name matched ticket ID",
    file_overlap:"Files touched match ticket's PR",
    temporal_proximity:"Session active while ticket was In Progress",
    developer_match:"Session developer = ticket assignee",
    explicit_mention:"Ticket ID in commit message or PR",
  };

  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
      `}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        {/* Breadcrumb header */}
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"14px 28px",display:"flex",alignItems:"center",gap:12}}>
          <button style={{background:"none",border:"none",cursor:"pointer",color:C.sub,display:"flex",alignItems:"center",gap:5,fontFamily:F.body,fontSize:12}}>
            <ArrowLeft size={14}/> JIRA-142
          </button>
          <span style={{color:C.muted}}>·</span>
          <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>Session Detail</span>
          <span style={{marginLeft:"auto",fontFamily:F.mono,fontSize:11,color:C.sub}}>{session.session_id.slice(0,24)}…</span>
        </div>

        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          {/* Session header card */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,padding:"16px 20px"}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:16}}>
              <div style={{display:"flex",gap:14,alignItems:"center"}}>
                {/* Avatar */}
                <div style={{width:42,height:42,borderRadius:"50%",background:`${session.developer.color}15`,border:`2px solid ${session.developer.color}40`,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:F.mono,fontSize:14,fontWeight:700,color:session.developer.color}}>
                  {session.developer.avatar}
                </div>
                <div>
                  <div style={{fontFamily:F.ui,fontSize:16,fontWeight:600,color:C.text}}>{session.developer.name}</div>
                  <div style={{display:"flex",gap:10,marginTop:3,alignItems:"center"}}>
                    <Tag color={C.accent} bg={C.accentBg}>{session.tool.name}</Tag>
                    <Tag color={C.purple} bg={C.purpleBg}>{session.tool.model}</Tag>
                    <Tag color={C.green} bg={C.greenBg}>local_exact</Tag>
                  </div>
                </div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontFamily:F.mono,fontSize:24,fontWeight:600,color:C.warm}}>${session.tokens.total_cost_usd.toFixed(2)}</div>
                <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>
                  {session.tokens.reconciled?"✓ reconciled":"⏳ estimated"}
                </div>
              </div>
            </div>
            {/* Timeline bar */}
            <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:14}}>
              {[
                {label:"Started",value:"09:28 AM"},
                {label:"→",value:"",mono:false},
                {label:"First commit",value:"10:55 AM"},
                {label:"→",value:"",mono:false},
                {label:"Ended",value:"10:42 AM"},
              ].map((item,i)=>(
                item.label==="→"
                  ?<ChevronRight key={i} size={14} color={C.muted}/>
                  :<div key={i}>
                    <div style={{fontFamily:F.body,fontSize:9,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:2}}>{item.label}</div>
                    <div style={{fontFamily:F.mono,fontSize:12,color:C.text}}>{item.value}</div>
                  </div>
              ))}
              <div style={{marginLeft:"auto",fontFamily:F.mono,fontSize:12,color:C.accent}}>
                {session.timing.active_duration_min}min active
              </div>
            </div>
            {/* Attribution */}
            <div style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.15)`,borderRadius:8,padding:"10px 14px",display:"flex",alignItems:"center",gap:12}}>
              <GitCommit size={14} color={C.accent}/>
              <div style={{flex:1}}>
                <span style={{fontFamily:F.mono,fontSize:12,color:C.accent}}>{session.attribution.ticket_id}</span>
                <span style={{fontFamily:F.body,fontSize:12,color:C.text,marginLeft:10}}>{session.attribution.ticket_title}</span>
              </div>
              <div style={{display:"flex",gap:8,alignItems:"center"}}>
                <Tag color={C.green} bg={C.greenBg}>{Math.round(session.attribution.confidence*100)}% confidence</Tag>
                <Tag color={C.sub} bg={C.muted}>{session.attribution.method.replace("_"," ")}</Tag>
              </div>
            </div>
          </div>

          {/* Stat grid */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:10}}>
            <StatCard label="Input tokens" value={session.tokens.input.toLocaleString()} color={C.text}/>
            <StatCard label="Output tokens" value={session.tokens.output.toLocaleString()} color={C.text}/>
            <StatCard label="Cache reads" value={session.tokens.cache_read.toLocaleString()} sub="Claude Code" color={C.purple}/>
            <StatCard label="Turn count" value={session.activity.turn_count.toString()} color={C.text}/>
            <StatCard label="Files touched" value={session.activity.files_touched_count.toString()} color={C.text}/>
            <StatCard label="Subagents" value={session.activity.subagent_count.toString()} sub="spawned" color={C.accent}/>
          </div>

          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
            {/* Turn-level token chart */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
              <div style={{padding:"14px 18px 10px"}}>
                <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Per-Turn Token Usage</div>
                <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Input tokens per turn — Claude Code exact data</div>
              </div>
              <Divider/>
              <div style={{padding:"14px 18px"}}>
                <div style={{display:"flex",gap:3,alignItems:"flex-end",height:80}}>
                  {session.turns.map((t,i)=>{
                    const h=(t.input/maxInput)*76+4;
                    const isSpike=t.input>500;
                    return(
                      <div key={i} title={`Turn ${t.turn}: ${t.input} input, ${t.output} output`} style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:3}}>
                        <div style={{width:"100%",height:`${h}px`,background:isSpike?C.amber:C.accent,borderRadius:"2px 2px 0 0",opacity:isSpike?0.9:0.65,transition:"opacity .1s",cursor:"pointer"}}
                          onMouseEnter={e=>(e.currentTarget.style.opacity="1")}
                          onMouseLeave={e=>(e.currentTarget.style.opacity=isSpike?"0.9":"0.65")}
                        />
                      </div>
                    );
                  })}
                </div>
                <div style={{display:"flex",gap:3,marginTop:4}}>
                  {session.turns.map(t=>(
                    <div key={t.turn} style={{flex:1,textAlign:"center",fontFamily:F.mono,fontSize:8,color:C.sub}}>{t.turn}</div>
                  ))}
                </div>
                <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginTop:8}}>Turn 1 had highest token count (1,240) — initial context loading. No spikes detected.</div>
              </div>
            </div>

            {/* Code output + quality */}
            <div style={{display:"flex",flexDirection:"column",gap:14}}>
              <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
                <div style={{padding:"12px 16px 9px"}}>
                  <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Code Output</div>
                </div>
                <Divider/>
                <div style={{padding:"12px 16px",display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                  {[
                    {l:"Lines added",v:`+${session.code_output.lines_added}`,c:C.green},
                    {l:"Lines deleted",v:`-${session.code_output.lines_deleted}`,c:C.red},
                    {l:"Lines accepted",v:session.code_output.lines_accepted.toString(),c:C.accent},
                    {l:"Lines reverted",v:session.code_output.lines_reverted.toString(),c:C.amber},
                  ].map((s,i)=>(
                    <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"7px 10px",background:C.surface,borderRadius:6}}>
                      <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{s.l}</span>
                      <span style={{fontFamily:F.mono,fontSize:13,fontWeight:600,color:s.c}}>{s.v}</span>
                    </div>
                  ))}
                </div>
                <Divider/>
                <div style={{padding:"10px 16px"}}>
                  <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:6}}>Commit hashes</div>
                  {session.code_output.commit_hashes.map((h,i)=>(
                    <div key={i} style={{fontFamily:F.mono,fontSize:11,color:C.accent,marginBottom:3}}>{h}</div>
                  ))}
                </div>
              </div>
              <div style={{background:C.card,border:`1px solid ${session.quality.hallucination_risk==="none"?C.border:"rgba(0,230,118,0.2)"}`,borderRadius:10,padding:"12px 16px"}}>
                <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text,marginBottom:10}}>Quality Signals</div>
                {[
                  {l:"Hallucination risk",v:session.quality.hallucination_risk,ok:session.quality.hallucination_risk==="none"},
                  {l:"Token spike",v:session.quality.token_spike_detected?"Detected":"None detected",ok:!session.quality.token_spike_detected},
                  {l:"File oscillations",v:`${session.quality.file_oscillations} file(s)`,ok:session.quality.file_oscillations<3},
                  {l:"Session restarts",v:session.quality.session_restarts.toString(),ok:session.quality.session_restarts===0},
                  {l:"Committed at end",v:session.code_output.is_committed?"Yes":"No",ok:session.code_output.is_committed},
                ].map((q,i)=>(
                  <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:7}}>
                    <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{q.l}</span>
                    <div style={{display:"flex",alignItems:"center",gap:5}}>
                      {q.ok?<CheckCircle2 size={11} color={C.green}/>:<AlertTriangle size={11} color={C.amber}/>}
                      <span style={{fontFamily:F.mono,fontSize:11,color:q.ok?C.green:C.amber}}>{q.v}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Files + Attribution signals */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
              <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Files Touched</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>File paths only — no code content stored</div></div>
              <Divider/>
              <div style={{padding:"8px 0"}}>
                {session.activity.files_touched.map((f,i)=>(
                  <div key={i}>
                    <div style={{padding:"9px 16px",display:"flex",alignItems:"center",gap:10}}>
                      <FileCode size={12} color={C.sub}/>
                      <span style={{fontFamily:F.mono,fontSize:11,color:C.text}}>{f}</span>
                    </div>
                    {i<session.activity.files_touched.length-1&&<Divider/>}
                  </div>
                ))}
              </div>
            </div>
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
              <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Attribution Signals</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Why this session was attributed to JIRA-142</div></div>
              <Divider/>
              <div style={{padding:"8px 0"}}>
                {(["branch_match","file_overlap","temporal_proximity","developer_match","explicit_mention"] as const).map((signal,i)=>{
                  const fired=session.attribution.signals.includes(signal);
                  return(
                    <div key={i}>
                      <div style={{padding:"10px 16px",display:"flex",alignItems:"center",gap:10,opacity:fired?1:0.4}}>
                        {fired?<CheckCircle2 size={13} color={C.green}/>:<XCircle size={13} color={C.sub}/>}
                        <span style={{fontFamily:F.body,fontSize:12,color:fired?C.text:C.sub}}>{signalLabels[signal]}</span>
                        {fired&&<Tag color={C.green} bg={C.greenBg} style={{marginLeft:"auto"}}>fired</Tag>}
                      </div>
                      {i<4&&<Divider/>}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Meta */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 16px",display:"flex",gap:20,alignItems:"center"}}>
            <div><span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Captured: </span><span style={{fontFamily:F.mono,fontSize:11,color:C.text}}>2026-05-28 10:43:00 UTC</span></div>
            <div><span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Agent: </span><span style={{fontFamily:F.mono,fontSize:11,color:C.text}}>v{session.meta.agent_version}</span></div>
            <div><span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Data sources: </span><span style={{fontFamily:F.mono,fontSize:11,color:C.text}}>{session.meta.data_sources.join(", ")}</span></div>
            <div><span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Schema: </span><span style={{fontFamily:F.mono,fontSize:11,color:C.text}}>v{session.meta.schema_version}</span></div>
            <div style={{marginLeft:"auto"}}><Tag color={C.green} bg={C.greenBg}>reconciled ✓</Tag></div>
          </div>
        </div>
      </div>
    </>
  );
}
