/**
 * S-05 Capacity Overview
 * AI-assisted vs human cycle time, lifecycle decomposition,
 * sprint velocity, PR pipeline health.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/capacity?sprint_range=4&team_id=all
 *   Coding agent: replace MOCK_CAPACITY with api.get('/capacity')
 */

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, ResponsiveContainer,
  Tooltip, CartesianGrid, BarChart, Bar,
} from "recharts";
import { GitPullRequest, Zap, ArrowUpRight } from "lucide-react";

const C = {
  bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",
  accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",
  warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",
  green:"#00E676",greenBg:"rgba(0,230,118,0.08)",
  red:"#FF4545",redBg:"rgba(255,69,69,0.08)",
  amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",
  purple:"#A78BFA",purpleBg:"rgba(167,139,250,0.08)",
  text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",
  border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)",
} as const;

const F = {
  ui:"'Outfit', sans-serif",
  body:"'DM Sans', sans-serif",
  mono:"'JetBrains Mono', monospace",
};

// GET /api/v1/capacity?sprint_range=4
const MOCK_CAPACITY = {
  cycle_time:[
    {sprint:"S39",ai_hours:8.2,human_hours:12.4},
    {sprint:"S40",ai_hours:7.8,human_hours:12.8},
    {sprint:"S41",ai_hours:6.1,human_hours:12.2},
    {sprint:"S42",ai_hours:4.8,human_hours:11.9},
  ],
  lifecycle:{
    ai:{prompt_to_commit:1.2,commit_to_pr:0.8,pr_to_review:1.4,review_to_merge:1.4,total:4.8},
    human:{commit_to_pr:3.2,pr_to_review:4.8,review_to_merge:3.9,total:11.9},
  },
  velocity:[
    {sprint:"S37",ai_points:18,human_points:24},
    {sprint:"S38",ai_points:22,human_points:26},
    {sprint:"S39",ai_points:28,human_points:23},
    {sprint:"S40",ai_points:34,human_points:24},
    {sprint:"S41",ai_points:38,human_points:22},
    {sprint:"S42",ai_points:41,human_points:21},
  ],
  open_prs:[
    {id:"PR-284",title:"Stripe payment gateway",author:"Adnan K",ai_assisted:true,loc:980,open_hours:6.2,status:"in_review"},
    {id:"PR-283",title:"Data pipeline refactor",author:"Sara P",ai_assisted:true,loc:2100,open_hours:31.4,status:"needs_work"},
    {id:"PR-281",title:"Auth SSO integration",author:"Raj K",ai_assisted:true,loc:720,open_hours:4.1,status:"in_review"},
    {id:"PR-279",title:"Search & filter API",author:"Priya M",ai_assisted:false,loc:380,open_hours:8.8,status:"approved"},
    {id:"PR-276",title:"Fix auth token refresh",author:"Vikram S",ai_assisted:false,loc:140,open_hours:2.1,status:"approved"},
  ],
  summary:{ai_cycle_time_hrs:4.8,human_cycle_time_hrs:11.9,speedup_factor:2.5,ai_prs:8,human_prs:4,avg_ai_pr_size:980,avg_human_pr_size:390},
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}
const CT=({active,payload,label}:any)=>{
  if(!active||!payload?.length)return null;
  return(
    <div style={{background:C.surface,border:`1px solid ${C.borderHi}`,borderRadius:8,padding:"10px 14px"}}>
      <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:6}}>{label}</div>
      {payload.map((p:any,i:number)=>(
        <div key={i} style={{display:"flex",alignItems:"center",gap:8,marginBottom:3,fontFamily:F.mono,fontSize:12,color:p.color,fontWeight:600}}>
          <span style={{width:8,height:8,borderRadius:2,background:p.color,flexShrink:0}}/>
          {p.name}: {p.value}h
        </div>
      ))}
    </div>
  );
};

function SummaryStrip(){
  const s=MOCK_CAPACITY.summary;
  const items=[
    {label:"AI Cycle Time",value:`${s.ai_cycle_time_hrs}h`,color:C.accent,note:"−3.4h vs S39"},
    {label:"Human Cycle Time",value:`${s.human_cycle_time_hrs}h`,color:C.sub,note:"−0.5h vs S39"},
    {label:"AI Speed Advantage",value:`${s.speedup_factor}×`,color:C.green,note:"+0.7× vs S39"},
    {label:"AI PRs This Sprint",value:`${s.ai_prs}`,color:C.purple,note:`of ${s.ai_prs+s.human_prs} total`},
    {label:"Avg AI PR Size",value:`${s.avg_ai_pr_size} LOC`,color:C.amber,note:`vs ${s.avg_human_pr_size} LOC human`},
  ];
  return(
    <div style={{display:"flex",background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
      {items.map((item,i)=>(
        <div key={i} style={{flex:1,padding:"14px 16px",borderRight:i<items.length-1?`1px solid ${C.border}`:"none"}}>
          <div style={{fontFamily:F.body,fontSize:9,color:C.sub,textTransform:"uppercase",letterSpacing:"0.07em",marginBottom:5}}>{item.label}</div>
          <div style={{fontFamily:F.mono,fontSize:19,fontWeight:600,color:item.color,lineHeight:1,marginBottom:4}}>{item.value}</div>
          <div style={{fontFamily:F.mono,fontSize:10,color:C.sub}}>{item.note}</div>
        </div>
      ))}
    </div>
  );
}

function CycleTimeChart(){
  return(
    <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
      <div style={{padding:"14px 18px 10px",display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
        <div>
          <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>AI-Assisted vs Human-Only Cycle Time</div>
          <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Weekly P50 cycle time (hours) · first commit → PR merge</div>
        </div>
        <div style={{display:"flex",gap:14}}>
          {[{color:C.accent,label:"AI-assisted"},{color:C.red,label:"Human-only"}].map((l,i)=>(
            <span key={i} style={{display:"flex",alignItems:"center",gap:6,fontFamily:F.body,fontSize:11,color:C.sub}}>
              <span style={{width:20,height:2,background:l.color,borderRadius:1,display:"inline-block"}}/>
              {l.label}
            </span>
          ))}
        </div>
      </div>
      <Divider/>
      <div style={{padding:"14px 8px 8px"}}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={MOCK_CAPACITY.cycle_time} margin={{top:8,right:24,bottom:0,left:-8}}>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false}/>
            <XAxis dataKey="sprint" tick={{fontSize:11,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
            <YAxis tick={{fontSize:11,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false} tickFormatter={v=>`${v}h`}/>
            <Tooltip content={<CT/>}/>
            <Line type="monotone" dataKey="ai_hours" name="AI-assisted" stroke={C.accent} strokeWidth={2.5}
              dot={{r:5,fill:C.accent,strokeWidth:0}} activeDot={{r:6,fill:C.accent,strokeWidth:2,stroke:C.bg}}/>
            <Line type="monotone" dataKey="human_hours" name="Human-only" stroke={C.red} strokeWidth={2}
              strokeDasharray="6 3" dot={{r:5,fill:C.red,strokeWidth:0}} activeDot={{r:6,fill:C.red,strokeWidth:2,stroke:C.bg}}/>
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Divider/>
      <div style={{padding:"10px 18px",display:"flex",alignItems:"center",gap:8,background:C.accentBg}}>
        <Zap size={13} color={C.accent}/>
        <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>
          AI-assisted PRs close <span style={{color:C.accent,fontFamily:F.mono,fontWeight:600}}>2.5× faster</span> — gap widening sprint over sprint
        </span>
      </div>
    </div>
  );
}

function LifecycleChart(){
  const lc=MOCK_CAPACITY.lifecycle;
  const stages=[
    {key:"prompt_to_commit",label:"Prompt → Commit",color:C.warm},
    {key:"commit_to_pr",label:"Commit → PR",color:C.accent},
    {key:"pr_to_review",label:"PR → Review",color:C.purple},
    {key:"review_to_merge",label:"Review → Merge",color:C.green},
  ] as const;
  return(
    <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
      <div style={{padding:"14px 18px 10px"}}>
        <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Lifecycle Decomposition</div>
        <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Median hours per stage · AI vs human PRs</div>
      </div>
      <Divider/>
      <div style={{padding:"16px 18px"}}>
        {/* Human */}
        <div style={{marginBottom:18}}>
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:7}}>
            <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>Human-only</span>
            <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:C.sub}}>{lc.human.total}h total</span>
          </div>
          <div style={{display:"flex",gap:2,height:30,borderRadius:6,overflow:"hidden"}}>
            {stages.slice(1).map((s,i)=>{
              const val=(lc.human as any)[s.key]||0;
              const w=(val/lc.human.total)*100;
              return(
                <div key={i} title={`${s.label}: ${val}h`} style={{width:`${w}%`,background:s.color,opacity:.45,display:"flex",alignItems:"center",justifyContent:"center"}}>
                  <span style={{fontFamily:F.mono,fontSize:9,color:"#000",fontWeight:700}}>{val}h</span>
                </div>
              );
            })}
          </div>
        </div>
        {/* AI */}
        <div style={{marginBottom:16}}>
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:7}}>
            <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>AI-assisted</span>
            <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:C.accent}}>{lc.ai.total}h total</span>
          </div>
          <div style={{display:"flex",gap:2,height:30,borderRadius:6,overflow:"hidden",width:`${(lc.ai.total/lc.human.total)*100}%`}}>
            {stages.map((s,i)=>{
              const val=(lc.ai as any)[s.key]||0;
              if(!val)return null;
              const w=(val/lc.ai.total)*100;
              return(
                <div key={i} title={`${s.label}: ${val}h`} style={{width:`${w}%`,background:s.color,opacity:.85,display:"flex",alignItems:"center",justifyContent:"center"}}>
                  <span style={{fontFamily:F.mono,fontSize:9,color:"#000",fontWeight:700}}>{val}h</span>
                </div>
              );
            })}
          </div>
        </div>
        {/* Legend */}
        <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
          {stages.map((s,i)=>(
            <span key={i} style={{display:"flex",alignItems:"center",gap:5,fontFamily:F.body,fontSize:10,color:C.sub}}>
              <span style={{width:9,height:9,borderRadius:2,background:s.color,opacity:.8}}/>
              {s.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function VelocityChart(){
  return(
    <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
      <div style={{padding:"14px 18px 10px"}}>
        <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Sprint Velocity</div>
        <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Story points completed · AI vs human contribution</div>
      </div>
      <Divider/>
      <div style={{padding:"12px 8px 8px"}}>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={MOCK_CAPACITY.velocity} margin={{top:4,right:16,bottom:0,left:-12}}>
            <XAxis dataKey="sprint" tick={{fontSize:10,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
            <YAxis tick={{fontSize:10,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
            <Tooltip contentStyle={{background:C.surface,border:`1px solid ${C.borderHi}`,borderRadius:7,fontFamily:F.mono,fontSize:11}} labelStyle={{color:C.sub}}/>
            <Bar dataKey="ai_points" name="AI-attributed" stackId="v" fill={C.accent} fillOpacity={0.75} radius={[0,0,0,0]}/>
            <Bar dataKey="human_points" name="Human-only" stackId="v" fill={C.muted} fillOpacity={0.8} radius={[3,3,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Divider/>
      <div style={{padding:"9px 18px",display:"flex",gap:16}}>
        {[{color:C.accent,label:"AI-attributed points"},{color:C.muted,label:"Human-only points"}].map((l,i)=>(
          <span key={i} style={{display:"flex",alignItems:"center",gap:6,fontFamily:F.body,fontSize:11,color:C.sub}}>
            <span style={{width:10,height:10,borderRadius:2,background:l.color}}/>
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function PRPipeline(){
  const [hov,setHov]=useState<number|null>(null);
  const statusCfg:Record<string,{label:string;color:string;bg:string}>={
    in_review:{label:"In review",color:C.accent,bg:C.accentBg},
    needs_work:{label:"Needs work",color:C.red,bg:C.redBg},
    approved:{label:"Approved",color:C.green,bg:C.greenBg},
  };
  return(
    <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
      <div style={{padding:"14px 18px 10px"}}>
        <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Open PR Pipeline</div>
        <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Sprint 42 · open pull requests and review status</div>
      </div>
      <Divider/>
      <div style={{display:"grid",gridTemplateColumns:"80px 1fr 80px 80px 80px 90px",gap:10,padding:"6px 18px"}}>
        {["PR","Title","Author","Type","Open for","Status"].map(h=>(
          <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:600}}>{h}</span>
        ))}
      </div>
      <Divider/>
      {MOCK_CAPACITY.open_prs.map((pr,i)=>{
        const st=statusCfg[pr.status];
        const tooOld=pr.open_hours>24;
        return(
          <div key={i}>
            <div onMouseEnter={()=>setHov(i)} onMouseLeave={()=>setHov(null)}
              style={{display:"grid",gridTemplateColumns:"80px 1fr 80px 80px 80px 90px",gap:10,padding:"11px 18px",alignItems:"center",background:hov===i?C.hover:"transparent",cursor:"pointer",transition:"background .1s"}}>
              <span style={{fontFamily:F.mono,fontSize:12,color:C.accent}}>{pr.id}</span>
              <span style={{fontFamily:F.body,fontSize:12,color:C.text,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{pr.title}</span>
              <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{pr.author}</span>
              {pr.ai_assisted
                ?<Tag color={C.accent} bg={C.accentBg}>AI</Tag>
                :<Tag color={C.sub} bg="rgba(90,90,90,0.1)">Human</Tag>}
              <span style={{fontFamily:F.mono,fontSize:12,color:tooOld?C.amber:C.text}}>
                {pr.open_hours<24?`${pr.open_hours}h`:`${(pr.open_hours/24).toFixed(1)}d`}{tooOld?" ⚠":""}
              </span>
              <Tag color={st.color} bg={st.bg}>{st.label}</Tag>
            </div>
            {i<MOCK_CAPACITY.open_prs.length-1&&<Divider/>}
          </div>
        );
      })}
      <Divider/>
      <div style={{padding:"9px 18px",display:"flex",alignItems:"center",gap:8}}>
        <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>1 PR blocked · 1 PR oversized (&gt;1500 LOC) · 2 pending review</span>
        <span style={{marginLeft:"auto",fontFamily:F.body,fontSize:11,color:C.accent,cursor:"pointer",display:"flex",alignItems:"center",gap:3}}>
          View all PRs <GitPullRequest size={12}/>
        </span>
      </div>
    </div>
  );
}

export default function CapacityOverview(){
  const [sprintRange,setSprintRange]=useState<"4"|"8"|"12">("4");
  const [source,setSource]=useState<"Linear"|"Jira">("Linear");
  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
      `}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Insights · Capacity Overview</div>
            <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Capacity Overview</h1>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>See where each team spends its hours and where bandwidth opens next sprint</div>
          </div>
          <div style={{display:"flex",gap:8}}>
            <div style={{display:"flex",background:C.card,border:`1px solid ${C.border}`,borderRadius:7,overflow:"hidden"}}>
              {(["Linear","Jira"] as const).map(s=>(
                <button key={s} onClick={()=>setSource(s)} style={{background:source===s?C.surface:"none",border:"none",cursor:"pointer",fontFamily:F.body,fontSize:12,color:source===s?C.text:C.sub,padding:"6px 14px"}}>
                  {s}
                </button>
              ))}
            </div>
            {(["4","8","12"] as const).map(n=>(
              <button key={n} onClick={()=>setSprintRange(n)} style={{background:sprintRange===n?C.accentBg:"none",border:`1px solid ${sprintRange===n?"rgba(0,212,255,0.3)":C.border}`,borderRadius:7,padding:"6px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:sprintRange===n?C.accent:C.sub}}>
                Last {n} sprints
              </button>
            ))}
          </div>
        </div>
        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          <SummaryStrip/>
          <div style={{display:"grid",gridTemplateColumns:"3fr 2fr",gap:14}}>
            <CycleTimeChart/>
            <LifecycleChart/>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
            <VelocityChart/>
            <PRPipeline/>
          </div>
        </div>
      </div>
    </>
  );
}
