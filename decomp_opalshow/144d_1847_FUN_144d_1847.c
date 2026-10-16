
uint * __cdecl16near FUN_144d_1847(void)

{
  char *pcVar1;
  uint *puVar2;
  uint uVar3;
  uint uVar4;
  int iVar5;
  int in_CX;
  uint uVar6;
  undefined2 *in_BX;
  uint *puVar7;
  uint *puVar8;
  uint *puVar9;
  uint *puVar10;
  undefined2 unaff_ES;
  uint *unaff_SS;
  uint *unaff_DS;
  bool bVar11;
  
  if ((in_CX + 1U != 0) && (uVar6 = in_CX + 1U & 0xfffe, uVar6 < 0xffee)) {
    puVar10 = (uint *)in_BX[1];
    puVar7 = puVar10 + 1;
    uVar4 = *puVar10;
    puVar8 = puVar7;
    if ((uVar4 & 1) != 0) {
      do {
        uVar3 = uVar4 - 1;
        bVar11 = uVar3 == uVar6;
        if (uVar6 <= uVar3) {
LAB_144d_1877:
          if (bVar11) {
            *(char *)(puVar7 + -1) = (char)puVar7[-1] + -1;
          }
          else {
            puVar7[-1] = uVar6;
            *(int *)((int)puVar7 + uVar6) = (uVar3 - uVar6) + -1;
          }
          if (unaff_DS != unaff_SS) {
            *(undefined2 *)0x5b2 = unaff_DS;
          }
          in_BX[1] = (int)puVar7 + uVar6;
          return (uint *)CONCAT22(unaff_DS,puVar7);
        }
        puVar8 = (uint *)((int)puVar7 + uVar3) + 1;
        uVar4 = *(uint *)((int)puVar7 + uVar3);
        if ((uVar4 & 1) == 0) break;
        uVar4 = uVar4 + uVar3 + 2;
        *puVar10 = uVar4;
      } while( true );
    }
    *(undefined1 *)0x5b8 = 2;
    puVar10 = puVar7;
    do {
      if (uVar4 == 0xfffe) {
        puVar7 = (uint *)in_BX[4];
        if (puVar7 == (uint *)0x0) {
          pcVar1 = (char *)0x5b8;
          *pcVar1 = *pcVar1 + -1;
          if (*pcVar1 == '\0') {
            uVar4 = in_BX[3];
            uVar3 = FUN_144d_1964();
            bVar11 = uVar3 == uVar4;
            if (!bVar11) {
              bVar11 = (uVar3 & 0xff01) == 0xfffe;
              FUN_144d_1964();
              if (bVar11) break;
              puVar2 = puVar10 + -1;
              *(char *)puVar2 = (char)*puVar2 + -1;
              bVar11 = (char)*puVar2 == '\0';
            }
            iVar5 = FUN_144d_192a();
            if (!bVar11) {
              puVar9 = (uint *)(iVar5 + -2);
              goto LAB_144d_18ae;
            }
            break;
          }
          puVar10 = unaff_SS;
          puVar7 = unaff_DS;
          if (unaff_DS != unaff_SS) {
            puVar7 = (uint *)*(undefined2 *)0x5ae;
          }
        }
        puVar9 = (uint *)*in_BX;
        unaff_DS = puVar7;
      }
      else {
        puVar9 = (uint *)((int)puVar8 + uVar4);
        puVar10 = puVar8;
      }
LAB_144d_18ae:
      puVar7 = puVar9 + 1;
      uVar4 = *puVar9;
      puVar8 = puVar7;
      if ((uVar4 & 1) != 0) {
        while( true ) {
          uVar3 = uVar4 - 1;
          bVar11 = uVar3 == uVar6;
          if (uVar6 <= uVar3) goto LAB_144d_1877;
          puVar8 = (uint *)((int)puVar7 + uVar3) + 1;
          uVar4 = *(uint *)((int)puVar7 + uVar3);
          puVar10 = puVar7;
          if ((uVar4 & 1) == 0) break;
          uVar4 = uVar4 + uVar3 + 2;
          *puVar9 = uVar4;
        }
      }
    } while( true );
  }
  if (unaff_DS != unaff_SS) {
    *(undefined2 *)0x5b2 = unaff_DS;
  }
  in_BX[1] = *in_BX;
  return (uint *)0x0;
}

