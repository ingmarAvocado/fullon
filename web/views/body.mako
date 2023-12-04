<%
import arrow
%>

 <div class="container">
        <p></p>
    <h6>Current Active Bots BTC MARKETS</h6>
        <table id="fullon" class="display compact   table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    
                    <th colspan="8" style="text-align: center; vertical-align: middle;">Bot details</th>
                    <th colspan="5" style="text-align: center; vertical-align: middle;">Unrealised Activity<th>
                </tr>
                <tr>
                    <th>Symbol</th>
                    <th>Live</th>
                    <th>Strategy</th>
                    <th>Exchange</th>
                    <th>Av. Funds</th>
                    <th>Tot. Funds</th>
                    <th>Tot. Roi</th>
                    <th>Tot. %</th>
                    <th>Tick</th>
                    <th>Size</th>
                    <th>Price</th>
                    <th>ROI</th>
                    <th>%</th>
                    <th>Last (UTC)</th>
                </tr>

            </thead>
            <tbody>
                % for bot in btcbots:
                <tr>
                    <td><a href='/detail?tempkey=${bot.bot_id}'>${bot.symbol}</a></td>
                    <%
                    flag="info"
                    if bot.live == "Yes":
                        flag="success"
                    %>
                    <td><p class="text-${flag}">${bot.live}<p></td>
                    <td>${bot.strategy}</td>
                    <td>${bot.exchange}</td>

                    <td>${bot.funds}</td>                   
                    <td>${bot.totfunds}</td>
                    <td>${bot.tot_roi}</td> 
                    <td>${bot.tot_pct}</td>
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
                    
                </tr>
                % endfor
            </tbody>
        </table>
    <p>
    <h6>Current Active Bots USD MARKETS</h6>
        <table id="fullon" class="display compact   table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    
                    <th colspan="8" style="text-align: center; vertical-align: middle;">Bot details</th>
                    <th colspan="5" style="text-align: center; vertical-align: middle;">Unrealised Activity<th>
                </tr>
                <tr>
                    <th>Symbol</th>
                    <th>Live</th>
                    <th>Strategy</th>
                    <th>Exchange</th>
                    <th>Av. Funds</th>
                    <th>Tot. Funds</th>

                    <th>Tot. Roi</th>
                    <th>Tot. %</th>
                    <th>Tick</th>
                    <th>Size</th>
                    <th>Price</th>
                    <th>ROI</th>
                    <th>%</th>
                    <th>Last (UTC)</th>
                </tr>

            </thead>
            <tbody>
                % for bot in usdbots:
                <tr>
                    <td><a href='/detail?tempkey=${bot.bot_id}'>${bot.symbol}</a></td>
                    <%
                    flag="info"
                    if bot.live == "Yes":
                        flag="success"
                    %>
                    <td><p class="text-${flag}">${bot.live}<p></td>
                    <td>${bot.strategy}</td>
                    <td>${bot.exchange}</td>

                    <td>${bot.funds}</td>                   
                    <td>${bot.totfunds}</td>
                    <td>${bot.tot_roi}</td> 
                    <td>${bot.tot_pct}</td>
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
                    %>
                    <td><p class="text-${flag}">${bot.pos_pct}%</p></td>
                    <%
                        ts = arrow.get(bot.timestamp)
                        lateness = int(now.format('X')) - int(ts.format('X')) 
                        if lateness > 180 :
                            flag="warning"
                        else:
                            flag="success"
                    %>
                    <td><p class="text-${flag}">${ts.format('YYYY-MM-DD HH:mm:ss')}</p></td>
                    
                </tr>
                % endfor
            </tbody>
        </table>
        <p>


</div><!-- /.container --
