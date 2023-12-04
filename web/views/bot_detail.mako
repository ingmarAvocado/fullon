<%
import arrow
%>
<div class="container">
    <p></p>
    <h6>Bot Details</h6>
        <table id="fullon" class="display compact  table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Live</th>
                    <th>ROI</th>
                    <th>Fees</th>
                    <th>Since</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>${bot_view.name}</td>
                    <td>${bots[0].live}</td>
                    <td>${totals.roi}</td>
                    <td>${totals.fee}</td>
                    <td>${arrow.get(bots[0].timestamp).format('YYYY-MM-DD HH:mm:SS')}</td>
                </tr>               
            </tbody>
        </table>
   
 
    <p></p>

    <h6>Bot Current Status</h6>
        <table id="fullon" class="display compact  table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    <th>Av. Funds</th>
                    <th>Tot. Funds</th>
                    <th>Symbol</th>
                    <th>Tick</th>
                    <th>Size</th>
                    <th>Price</th>
                    <th>ROI</th>
                    <th>%</th>
                    <th>Last (UTC)</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                    % for bot in bots: 
                        <tr> 
                            <td>${bot.funds}</td>                   
                            <td>${bot.totfunds}</td>
                            <td>${bot.symbol}</td>
                            <td>${bot.tick}</td>
                            <td>${bot.pos}</td>
                            <td>${bot.pos_price}</td>
                            <td>${bot.pos_roi}</td>
                            <%
                                flag="secondary"
                                if bot.pos_price != 0:
                                    if bot.pos_pct < 0:
                                        flag="danger"
                                    elif bot.pos_pct > 0:
                                        flag="success"
                                else:
                                    roi_pct = 0
                            %>
                            <td><p class="text-${flag}">${bot.pos_pct}%</p></td>
                            <%
                                ts = arrow.get(bot.timestamp)
                                lateness = int(float(now.format('X'))) - int(float(ts.format('X'))) 
                                if lateness > 180 :
                                    flag="warning"
                                else:
                                    flag="success"
                            %>
                            <td><p class="text-${flag}">${ts.format('YYYY-MM-DD HH:mm:ss')}</p></td>
                            <td><p class="text-${flag}"><a href='log?tempkey=${bot.bot_id}&feed=${bot.feed}'>log</p></td>
                        </tr>
                    % endfor

                </tr>               
            </tbody>
        </table>
    
    <p></p>

    <h6>Bot Trade Overview (<a href='trades?tempkey=${bot.bot_id}'>Trade History</a>)</h6>


        <div class="main">
            <div id="chart" style="height: 250px;"></div>
        </div>


        <table id="fullon" class="display table-striped table-bordered" style="width:60%"> 
            <thead>
                <tr>
                    <th>Total Trades</th>
                    <th>0 to 5%</th>
                    <th>&gt; %5</th>
                    <th>0 to -5%</th>
                    <th>&lt; -5%</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>${ov.trades}</td>
                    <td>${ov.a}</td>
                    <td>${ov.b}</td>
                    <td>${ov.x}</td>
                    <td>${ov.y}</td>
                </tr>

            </tbody>
        </table>


    <p></p>
    <h6>Bot Strategy Details</h6>
    <table id="fullon" class="display compact " style="width:100%"> 
        <tr>
            <td style="vertical-align:top">
                <table id="fullon" class="display compact  table-striped table-bordered" style="width:100%"> 
                    <thead>
                        <tr>
                            <th>Param</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    % for param in str_params:
                        <tr>
                            <td>${param.name}</td><td>${param.value}</td>
                        </tr>
                    % endfor           
                </table>
            </td>
            <td style="vertical-align:top">            
                <table id="fullon" class="display compact  table-striped table-bordered" style="width:100%"> 
                    <thead>
                        <tr>
                            <th>Variable</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    % for var in str_vars:
                        <tr>
                            <%
                            if var.name == "timeout" and var.value != None:
                                line = f"<td>{var.name}</td><td>{arrow.get(var.value).format('YYYY-MM-DD HH:mm:ss')}</td>"
                            else:
                                line = f"<td>{var.name}</td><td>{var.value}</td>"
                            %>
                            ${line}
                        </tr>
                    % endfor           
                </table>

            </td>
        </tr>      
    </table>
</div>


<script>
Morris.Line({
  element: 'chart',
  data: [
    ${chart}
  ],
  xkey: 'date',
  ykeys: ['roi'],
  lineWidth: 2,
  pointSize: 0
});;
</script>
